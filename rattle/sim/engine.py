from collections import OrderedDict
from ..primitive import PrimIndex, PrimBitIndex, PrimSlice
from ..bitvec import BitVec, X
from ..circuit import BlockAssign, BlockCond


class SimEngine:
    def __init__(self, *modules):
        self._root_modules = modules
        self._modules = set()
        self._storage_prims = set()

        self._assign_queue = OrderedDict()
        self._combinational_queue = OrderedDict()
        self._clocked_eval_queue = OrderedDict()

        self._clocked_assign_queue = OrderedDict()
        self._delayed_assign_queue = OrderedDict()

        self._change_enqueues = {}
        self._user_callbacks = {}

        self._initial_blocks = []

        self._values = {}

        self._old_clock_values = {}

        for module in modules:
            self._add_module_recursive(module)

        self._vcd_dumps = {}

        self.reset()

    def reset(self):
        for vcd in self._vcd_dumps.values():
            vcd.close()

        self._vcd_dumps = {}

        self._values = {
            storage: self._xval(storage)
            for storage in self._storage_prims}

        self._time = 0

        self._assign_queue.clear()
        self._combinational_queue.clear()
        self._clocked_eval_queue.clear()
        self._clocked_assign_queue.clear()
        self._delayed_assign_queue.clear()
        self._old_clock_values = {}

        self._user_callbacks.clear()

        for block in self._initial_blocks:
            self._apply_pokes(self._eval_block(block))

        for enqueues in self._change_enqueues.values():
            for queue, callback, params in enqueues:
                self._enqueue(queue, callback, params)

        self.step_combinational()

    def time(self):
        return self._time

    @staticmethod
    def _xval(storage):
        scalar = BitVec(storage.width, 0, -1)

        def recurse(dimensions):
            if not dimensions:
                return scalar
            else:
                next_dimensions = dimensions[:-1]
                return [
                    recurse(next_dimensions) for _ in range(dimensions[-1])]

        return recurse(storage.dimensions)

    def _add_module_recursive(self, module):
        if module in self._modules:
            raise RuntimeError('Module already added to simulation engine')

        module_data = module._module_data

        self._modules.add(module)

        self._storage_prims.update(module_data.storage_prims)

        self._add_circuit(module_data.circuit)

        for submodule in module_data.submodules:
            self._add_module_recursive(submodule)

    def _add_circuit(self, circuit):
        for storage, assignments in circuit.assign.items():
            for lvalue, rvalue in assignments:
                self._add_assign(storage, lvalue, rvalue)
        for storage, block in circuit.combinational.items():
            self._add_combinational(storage, block)
        for clock, block in circuit.clocked.items():
            self._add_clocked(clock, block)

        for storage, block in circuit.initial.items():
            self._add_initial(storage, block)

        if circuit.async_reset:
            raise RuntimeError('Simulation of async reset not supported yet')

    def _add_assign(self, storage, lvalue, rvalue):
        enqueue = (
            self._assign_queue, self._eval_assign,
            (storage, lvalue, rvalue))
        for accessed_storage in rvalue.accessed_storage or [None]:
            enqueues = self._change_enqueues.setdefault(
                accessed_storage, [])

            enqueues.append(enqueue)

    def _add_combinational(self, storage, block):
        # pylint: disable=unused-argument
        enqueue = (
            self._combinational_queue, self._eval_combinational,
            block)
        for accessed_storage in block.accessed_storage or [None]:
            enqueues = self._change_enqueues.setdefault(accessed_storage, [])
            enqueues.append(enqueue)

    def _add_clocked(self, clock, block):
        enqueue = (
            self._clocked_eval_queue, self._eval_clocked,
            (clock, block))

        for accessed_storage in clock.accessed_storage:
            enqueues = self._change_enqueues.setdefault(accessed_storage, [])
            enqueues.append(enqueue)

    def _add_initial(self, storage, block):
        # pylint: disable=unused-argument
        self._initial_blocks.append(block)

    @staticmethod
    def _enqueue(queue, callback, params):
        key = (callback, params)
        try:
            queue.move_to_end(key)
        except KeyError:
            queue[key] = key

    def step_combinational(self):
        while True:
            # TODO configurable timeout
            if self._assign_queue:
                self._step_queue(self._assign_queue)
                continue
            if self._combinational_queue:
                self._step_queue(self._combinational_queue)
                continue
            break

    def step(self):
        self.step_combinational()
        while self._clocked_eval_queue:
            self._step_queue(self._clocked_eval_queue)
        stepped = bool(
            self._clocked_assign_queue or self._delayed_assign_queue)
        self._assign_queue.update(self._clocked_assign_queue)
        self._assign_queue.update(self._delayed_assign_queue)
        self._clocked_assign_queue.clear()
        self._delayed_assign_queue.clear()
        self.step_combinational()
        return stepped

    def advance_time(self, step):
        for vcd in self._vcd_dumps.values():
            vcd.update()
        self._time += step

    @staticmethod
    def _step_queue(queue):
        _key, (callback, parameters) = queue.popitem(last=False)
        callback(parameters)

    def _eval_assign(self, params):
        storage, lvalue, rvalue = params
        self.poke(storage, lvalue, self.peek(rvalue))

    def _eval_combinational(self, block):
        pokes = self._eval_block(block)
        self._apply_pokes(pokes)

    def _eval_clocked(self, params):
        clock, block = params

        clock_value = self.peek(clock)[0]
        old_clock_value = self._old_clock_values.get(clock, X)
        self._old_clock_values[clock] = clock_value

        if old_clock_value is False and clock_value is True:
            pokes = self._eval_block(block)
            self.poke_delayed(pokes)

    def peek(self, rvalue, indices=()):
        if rvalue in self._storage_prims:
            value = self._values[rvalue]
        elif isinstance(rvalue, PrimIndex):
            index = self.peek(rvalue.index)

            res = None
            index_range = rvalue.x.dimensions[len(indices)]
            for i in index.values():
                if i >= index_range:
                    res = BitVec(rvalue.x.width, 0, -1)
                    break
                value = self.peek(rvalue.x, indices + (i,))
                if res is None:
                    res = value
                else:
                    res = res.combine(value)
            return res
        else:
            value = rvalue.eval(self.peek)

        for idx in reversed(indices):
            value = value[idx]

        return value

    def poke(
            self, storage, lvalue, rvalue, *,
            indices=(), bitslice=None, xpoke=False, shadow=None):
        if lvalue in self._storage_prims:
            assert storage == lvalue
            if shadow is None:
                self._direct_poke(storage, rvalue, indices, bitslice, xpoke)
            else:
                if xpoke or bitslice is not None:
                    old_value = self._shadow_peek(shadow, lvalue, indices)
                if bitslice is not None:
                    rvalue = old_value.updated_at(bitslice, rvalue)
                if xpoke:
                    rvalue = rvalue.combine(old_value)
                shadow[(storage, indices)] = rvalue
        elif isinstance(lvalue, PrimIndex):
            index = self.peek(lvalue.index)
            index_range = lvalue.x.dimensions[len(indices)]
            if index.mask != 0:
                for i in index.values():
                    if i >= index_range:
                        self._poke_anywhere(
                            storage, lvalue, rvalue, indices, shadow)
                        break
                    self.poke(
                        storage, lvalue.x, rvalue,
                        indices=indices + (i,),
                        bitslice=bitslice,
                        xpoke=True, shadow=shadow)
            else:
                index = index.value
                if index >= index_range:
                    self._poke_anywhere(
                        storage, lvalue, rvalue, indices, shadow)
                else:
                    self.poke(
                        storage, lvalue.x, rvalue,
                        indices=indices + (index,),
                        bitslice=bitslice,
                        xpoke=xpoke, shadow=shadow)
        elif isinstance(lvalue, PrimSlice):
            self.poke(
                storage, lvalue.x, rvalue,
                indices=indices,
                bitslice=lvalue.start,
                xpoke=xpoke, shadow=shadow)
        elif isinstance(lvalue, PrimBitIndex):
            index = self.peek(lvalue.index)
            index_range = lvalue.x.width
            if index.mask != 0:
                for i in index.values():
                    if i >= index_range:
                        self.poke(
                            storage, lvalue.x, rvalue.repeat(lvalue.x.width),
                            indices=indices,
                            xpoke=True, shadow=shadow)
                        break
                    self.poke(
                        storage, lvalue.x, rvalue,
                        indices=indices,
                        bitslice=i,
                        xpoke=True, shadow=shadow)
            else:
                index = index.value
                if index >= index_range:
                    self.poke(
                        storage, lvalue.x, rvalue.repeat(lvalue.x.width),
                        indices=indices,
                        xpoke=True, shadow=shadow)
                else:
                    self.poke(
                        storage, lvalue.x, rvalue,
                        indices=indices,
                        bitslice=index,
                        xpoke=xpoke, shadow=shadow)
        else:
            raise RuntimeError('unexpected lvalue')

    def _poke_anywhere(self, storage, lvalue, rvalue, indices, shadow):
        assert isinstance(lvalue, PrimIndex)
        index_range = lvalue.x.dimensions[len(indices)]
        for i in range(index_range):
            self.poke(
                storage, lvalue.x, rvalue,
                indices=indices + (i,),
                xpoke=True, shadow=shadow)

    def _direct_poke(self, storage, rvalue, indices, bitslice, xpoke):
        key = storage
        values = self._values

        for idx in reversed(indices):
            values = values[key]
            key = idx

        old_value = values[key]

        if bitslice is not None:
            rvalue = old_value.updated_at(bitslice, rvalue)

        if xpoke:
            rvalue = rvalue.combine(old_value)
        values[key] = rvalue
        if not old_value.same_as(rvalue):
            for enqueue in self._change_enqueues.get(storage, ()):
                self._enqueue(*enqueue)
            for key, callback in self._user_callbacks.get(storage, {}).items():
                callback(key, storage)

    def _shadow_peek(self, shadow, storage, indices):
        try:
            return shadow[(storage, indices)]
        except KeyError:
            return self.peek(storage, indices)

    def _eval_block(self, block):
        shadow = OrderedDict()

        self._eval_block_assignments(block.assignments, shadow)

        return shadow

    def _eval_block_assignments(self, assignments, shadow):
        for statement in assignments:
            if isinstance(statement, BlockAssign):
                value = self.peek(statement.rvalue)
                self.poke(
                    statement.storage, statement.lvalue, value, shadow=shadow)
            elif isinstance(statement, BlockCond):
                condition_value = self.peek(statement.condition)[0]
                if condition_value is X:
                    shadow_copy = OrderedDict(shadow)
                    self._eval_block_assignments(statement.true, shadow)
                    self._eval_block_assignments(statement.false, shadow_copy)

                    self._merge_shadows(shadow, shadow_copy)
                else:
                    if condition_value:
                        branch = statement.true
                    else:
                        branch = statement.false

                    self._eval_block_assignments(branch, shadow)

    def _merge_shadows(self, shadow_a, shadow_b):
        for key, value_b in shadow_b.items():
            try:
                value_a = shadow_a[key]
            except KeyError:
                value_a = self.peek(*key)
            shadow_a[key] = value_a.combine(value_b)

        for key, value_a in shadow_a.items():
            if key not in shadow_b:
                shadow_a[key] = value_a.combine(self.peek(*key))

    def _apply_pokes(self, pokes):
        for (storage, indices), rvalue in pokes.items():
            self._direct_poke(storage, rvalue, indices, None, False)

    def poke_delayed(self, pokes):
        if pokes:
            self._delayed_assign_queue[object()] = (self._apply_pokes, pokes)

    def add_callback(self, storage, key, callback):
        try:
            callbacks = self._user_callbacks[storage]
        except KeyError:
            callbacks = self._user_callbacks[storage] = OrderedDict()
        callbacks[key] = callback

    def remove_callback(self, storage, key):
        try:
            del self._user_callbacks[storage][key]
            return True
        except KeyError:
            return False

    def dump_vcd_trace(self, trace, file):
        from .vcd import Vcd
        if trace in self._vcd_dumps:
            raise RuntimeError('trace is already being dumped')
        self._vcd_dumps[trace] = Vcd(self, trace, file)
