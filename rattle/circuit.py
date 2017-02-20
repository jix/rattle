from collections import OrderedDict, namedtuple


class Circuit:

    def __init__(self):
        self.combinational = OrderedDict()
        self.assign = OrderedDict()
        self.clocked = OrderedDict()
        self.async_reset = OrderedDict()
        self.sync_reset = OrderedDict()
        self.initial = OrderedDict()

        self.clocked_storage = {}

        self.finalized = False
        # TODO forbid modification after finalizing

    def add_combinational(self, storage, lvalue, condition, rvalue):
        storage = storage.simplify_read()
        try:
            block = self.combinational[storage]
        except KeyError:
            block = self.combinational[storage] = Block()
        block.add_assignment(storage, lvalue, condition, rvalue)

    def add_clocked(self, storage, clock, lvalue, condition, rvalue):
        storage = storage.simplify_read()
        try:
            block = self.clocked[clock]
        except KeyError:
            block = self.clocked[clock] = Block()
        block.add_assignment(storage, lvalue, condition, rvalue)
        self.clocked_storage.setdefault(storage, set()).add(clock)

    def add_sync_reset(self, storage, clock, reset, lvalue, rvalue):
        storage = storage.simplify_read()
        try:
            block = self.sync_reset[clock]
        except KeyError:
            block = self.sync_reset[clock] = Block()
        block.add_assignment(storage, lvalue, ((True, reset),), rvalue)
        self.clocked_storage.setdefault(storage, set()).add(clock)

    def add_async_reset(self, storage, clock, reset, lvalue, rvalue):
        storage = storage.simplify_read()
        try:
            block = self.async_reset[(clock, reset)]
        except KeyError:
            block = self.async_reset[(clock, reset)] = Block()
        block.add_assignment(storage, lvalue, (), rvalue)
        self.clocked_storage.setdefault(storage, set()).add(clock)

    def add_initial(self, storage, lvalue, rvalue):
        storage = storage.simplify_read()
        try:
            block = self.initial[storage]
        except KeyError:
            block = self.initial[storage] = Block()
        block.add_assignment(storage, lvalue, (), rvalue)

    @staticmethod
    def _opt_passes():
        from .opt.lower_sync_reset import LowerSyncReset
        from .opt.find_continuous_assignments import FindContinuousAssignments
        from .opt.reduce_bit_widths import ReduceBitWidths

        return [
            LowerSyncReset,
            FindContinuousAssignments,
            ReduceBitWidths,
        ]

    def finalize(self):
        if self.finalized:
            return

        for opt_pass in self._opt_passes():
            opt_pass(self)

        self.finalized = True

    def blocks(self):
        for block_dict in (
                self.combinational,
                self.clocked,
                self.async_reset,
                self.sync_reset,
                self.initial):
            yield from block_dict.values()

    def rvalues(self):
        for assignments in self.assign.values():
            for _lvalue, rvalue in assignments:
                yield rvalue

        for block in self.blocks():
            yield from block.rvalues()

    def map_rvalues(self, map_fn):
        for key, assignments in self.assign.items():
            self.assign[key] = [
                (lvalue, map_fn(rvalue)) for lvalue, rvalue in assignments]

        for block in self.blocks():
            block.map_rvalues(map_fn)

    def __repr__(self):
        lines = []
        lines.append('Circuit %s' % hex(id(self)))
        for storage, block in self.combinational.items():
            lines.append('combinational for %r:' % storage)
            lines.extend(block._repr_lines(indent='  '))
        for clock, block in self.clocked.items():
            lines.append('clocked for %r:' % clock)
            lines.extend(block._repr_lines(indent='  '))
        for clock, block in self.sync_reset.items():
            lines.append('sync reset for clock %r:' % clock)
            lines.extend(block._repr_lines(indent='  '))
        for (clock, reset), block in self.async_reset.items():
            lines.append('async reset %r for clock %r:' % (reset, clock))
            lines.extend(block._repr_lines(indent='  '))
        for storage, block in self.async_reset.items():
            lines.append('initial for %r:' % storage)
            lines.extend(block._repr_lines(indent='    '))
        return '\n'.join(lines)


BlockCond = namedtuple('BlockCond', 'condition true false')
BlockAssign = namedtuple('BlockAssign', 'storage lvalue rvalue')


class Block:
    def __init__(self):
        self.assignments = []
        self.storage = set()

    def add_assignment(self, storage, lvalue, condition, rvalue):
        position = self.assignments
        new_condition = ()

        for i, test in enumerate(condition):
            if (position and isinstance(position[-1], BlockCond)
                    and position[-1].condition == test[1]):
                if test[0]:
                    position = position[-1].true
                else:
                    position = position[-1].false
            else:
                new_condition = condition[i:]
                break

        for test in new_condition:
            if_node = BlockCond(test[1], [], [])
            position.append(if_node)
            if test[0]:
                position = if_node.true
            else:
                position = if_node.false

        position.append(BlockAssign(storage, lvalue, rvalue))
        self.storage.add(storage)

    def rvalues(self):
        def recurse(assignments):
            for statement in assignments:
                if isinstance(statement, BlockAssign):
                    yield statement.rvalue
                elif isinstance(statement, BlockCond):
                    yield statement.condition
                    yield from recurse(statement.true)
                    yield from recurse(statement.false)
                else:
                    assert False
        yield from recurse(self.assignments)

    def map_rvalues(self, map_fn):
        def recurse(assignments):
            for i, statement in enumerate(assignments):
                if isinstance(statement, BlockAssign):
                    assignments[i] = BlockAssign(
                        statement.storage,
                        statement.lvalue, map_fn(statement.rvalue))
                elif isinstance(statement, BlockCond):
                    assignments[i] = BlockCond(
                        map_fn(statement.condition),
                        statement.true,
                        statement.false)
                    recurse(statement.true)
                    recurse(statement.false)
                else:
                    assert False
        recurse(self.assignments)

    def __repr__(self):
        return '\n'.join(self._repr_lines())

    def _repr_lines(self, indent=''):
        lines = []

        def recurse(assignments, indent):
            if not assignments:
                lines.append('%spass' % indent)
                return
            for statement in assignments:
                if isinstance(statement, BlockAssign):
                    lines.append('%s%r := %r' % (
                        indent, statement.lvalue, statement.rvalue))
                elif isinstance(statement, BlockCond):
                    lines.append('%swhen %r:' % (
                        indent, statement.condition))
                    recurse(statement.true, indent + '  ')
                    lines.append('%selse:' % indent)
                    recurse(statement.false, indent + '  ')
                else:
                    assert False

        recurse(self.assignments, indent)
        return lines
