from contextlib import contextmanager
from ..type import BitsLike, Bits, BoolType, Vec, Bundle, Flip
from ..signal import Signal, StorageSignal, Value, Wire, Input, Output, IOPort
from ..reg import Reg
from ..hashutil import hash_key
from ..conditional import ResetCondition
from .. import expr


class LowerSettings:
    def __init__(self):
        pass


class LowerSignalGen:
    def __init__(
            self, root_signal,
            flipped=False, path=(), dimensions=(), indices=(),
            generated_signals=None):
        self.root_signal = root_signal
        self.flipped = flipped
        self.path = path
        self.dimensions = dimensions
        self.indices = indices
        if generated_signals is None:
            generated_signals = {}
            root_signal._lowered_parts = generated_signals
        self.generated_signals = generated_signals

    def clone(self):
        return LowerSignalGen(
            root_signal=self.root_signal,
            flipped=self.flipped,
            path=self.path,
            dimensions=self.dimensions,
            indices=self.indices,
            generated_signals=self.generated_signals,
        )

    def flip(self):
        result = self.clone()
        result.flipped = not self.flipped
        return result

    def enter(self, *path):
        result = self.clone()
        result.path += path
        return result

    def enter_vec(self, length):
        result = []
        for i in range(length):
            gen = self.clone()
            gen.dimensions += (length,)
            gen.indices += (i,)
            result.append(gen)
        return result

    def __call__(self, signal_type):
        # pylint: disable=redefined-variable-type
        try:
            signal = self.generated_signals[self.path]
        except KeyError:
            for dim in reversed(self.dimensions):
                signal_type = Vec(dim, signal_type)

            if isinstance(self.root_signal, Reg):
                signal = Reg(signal_type, clk=self.root_signal.clk)
            elif isinstance(self.root_signal, Wire):
                signal = Wire(signal_type)
            elif isinstance(self.root_signal, Input):
                if self.flipped:
                    signal = Output(signal_type)
                else:
                    signal = Input(signal_type)
            elif isinstance(self.root_signal, Output):
                if self.flipped:
                    signal = Input(signal_type)
                else:
                    signal = Output(signal_type)
            else:
                raise RuntimeError('unexpected Signal class during lowering')

            self.generated_signals[self.path] = signal

        for index in self.indices:
            signal = signal[index]

        return signal

    @contextmanager
    def lower_ioport_parent(self):
        signal = self.root_signal
        if isinstance(signal, IOPort) and signal.module.parent is not None:
            with signal.module.parent.reopen():
                yield
        else:
            yield


class Lower:
    def __init__(self, module, settings=LowerSettings()):
        self.module = module

        self.reduce_signal_cache = {}
        self.split_target_cache = {}

        for submodule in self.module._module_data.submodules:
            Lower(submodule, settings=settings)

        with self.module.reopen():
            # TODO Generate proxy Wires for named Values
            self.lower_storage_signals()
            self.lower_assignments()

    def lower_storage_signals(self):
        module_data = self.module._module_data
        storage_signals = module_data.storage_signals
        module_data.storage_signals = []
        for signal in storage_signals:
            self.lower_signal(signal)
            if signal._lowered is None:
                module_data.storage_signals.append(signal)
        module_data.lowered_storage_signals = module_data.storage_signals
        module_data.storage_signals = storage_signals

    def lower_signal(self, signal, signal_gen=None):
        if not self.signal_type_needs_lowering(signal.signal_type):
            return
        if signal_gen is None:
            signal_gen = LowerSignalGen(signal)

        signal._lowered = self.lower_signal_for_type(
            signal.signal_type, signal_gen)

    def lower_signal_for_type(self, signal_type, signal_gen):
        if not self.signal_type_needs_lowering(signal_type):
            lowered = signal_gen(signal_type)
            return lowered, lowered

        if isinstance(signal_type, Bundle):
            lowered, lowered_parent = self.lower_bundle(
                signal_type, signal_gen)
        elif isinstance(signal_type, Flip):
            lowered, lowered_parent = self.lower_flip(
                signal_type, signal_gen)
        elif isinstance(signal_type, Vec):
            lowered, lowered_parent = self.lower_vec(
                signal_type, signal_gen)
        else:
            raise RuntimeError(
                'signal of type %r cannot be lowered' % signal_type)

        return lowered, lowered_parent

    def signal_type_needs_lowering(self, signal_type):
        # TODO Memoization
        if isinstance(signal_type, (BitsLike, BoolType)):
            return False
        elif isinstance(signal_type, (Bundle, Flip)):
            return True
        elif isinstance(signal_type, Vec):
            return self.signal_type_needs_lowering(signal_type.element_type)

    def lower_bundle(self, signal_type, signal_gen):
        lowered_signals = {}
        lowered_signals_parent = {}
        for name, field_type in signal_type.fields.items():
            field_signal_gen = signal_gen.enter(name)
            lowered_field, lowered_field_parent = self.lower_signal_for_type(
                field_type, field_signal_gen)

            lowered_signals[name] = lowered_field
            lowered_signals_parent[name] = lowered_field_parent

        result = Value._auto_concat_lvalue(
            lowered_signals.values(),
            signal_type, expr.Bundle(lowered_signals))

        with signal_gen.lower_ioport_parent():
            result_parent = Value._auto_concat_lvalue(
                lowered_signals_parent.values(),
                signal_type, expr.Bundle(lowered_signals_parent))

        return result, result_parent

    def lower_flip(self, signal_type, signal_gen):
        unflipped_type = signal_type.unflipped

        flipped_signal_gen = signal_gen.flip()

        lowered, lowered_parent = self.lower_signal_for_type(
            unflipped_type, flipped_signal_gen)

        result = lowered.flip()

        with signal_gen.lower_ioport_parent():
            result_parent = lowered_parent.flip()

        return result, result_parent

    def lower_vec(self, signal_type, signal_gen):
        element_type = signal_type.element_type
        lowered_signals = []
        lowered_signals_parent = []

        item_signal_gens = signal_gen.enter_vec(signal_type.length)

        for item_signal_gen in item_signal_gens:
            lowered_element, lowered_element_parent = (
                self.lower_signal_for_type(element_type, item_signal_gen))

            lowered_signals.append(lowered_element)
            lowered_signals_parent.append(lowered_element_parent)

        result = Value._auto_concat_lvalue(
            lowered_signals,
            signal_type, expr.Vec(lowered_signals))

        with signal_gen.lower_ioport_parent():
            result_parent = Value._auto_concat_lvalue(
                lowered_signals_parent,
                signal_type, expr.Vec(lowered_signals_parent))

        return result, result_parent

    def lower_assignments(self):
        for assignment in sorted(
                self.module._module_data.assignments,
                key=lambda assignment: assignment[1]):
            target, _, conditions, value = assignment
            self.lower_assignment(target, conditions, value)

    def lower_assignment(self, target, conditions, value):
        target = self.reduce_signal(target, is_target=True)
        value = self.reduce_signal(value)
        conditions = tuple(
            (polarity, self.reduce_signal(condition))
            for polarity, condition in conditions)

        self.split_assignment(target, conditions, value)

    def reduce_signal(self, signal, is_target=False):
        key = hash_key(signal)
        try:
            return self.reduce_signal_cache[(is_target, key)]
        except KeyError:
            pass

        if isinstance(signal, StorageSignal):
            if signal._lowered is not None:
                if signal.module is self.module:
                    signal = signal._lowered[0]
                else:
                    signal = signal._lowered[1]
                signal = self.reduce_signal(signal, is_target)
        elif isinstance(signal, Value):
            signal = getattr(self, 'reduce_signal_' + signal.expr.fn_name)(
                signal, is_target, *signal.expr)

        self.reduce_signal_cache[(is_target, key)] = signal
        self.reduce_signal_cache[(is_target, hash_key(signal))] = signal

        return signal

    def reduce_signal_basic_op(self, signal, is_target, *params):
        return signal._auto_rewrite(type(signal.expr)(*tuple(
            self.reduce_signal(x, is_target) if isinstance(x, Signal) else x
            for x in params)))

    reduce_signal_nop = reduce_signal_basic_op  # TODO Handle nop
    reduce_signal_const_slice = reduce_signal_basic_op  # TODO Needs reduction?
    reduce_signal_concat = reduce_signal_basic_op
    reduce_signal_not = reduce_signal_basic_op
    reduce_signal_and = reduce_signal_basic_op
    reduce_signal_or = reduce_signal_basic_op
    reduce_signal_xor = reduce_signal_basic_op
    reduce_signal_sign_ext = reduce_signal_basic_op
    reduce_signal_zero_ext = reduce_signal_basic_op

    def reduce_signal_vec(self, signal, is_target, elements):
        return signal._auto_rewrite(expr.Vec(tuple(
            self.reduce_signal(element, is_target)
            for element in elements)))

    def reduce_signal_bundle(self, signal, is_target, fields):
        return signal._auto_rewrite(expr.Bundle(dict(
            (name, self.reduce_signal(field, is_target))
            for name, field in fields.items())))

    def reduce_signal_const_index(self, signal, is_target, index, x):
        signal = signal._auto_rewrite(
            expr.ConstIndex(index, self.reduce_signal(x, is_target=is_target)))

        if (isinstance(signal, Value) and
                isinstance(signal.expr.x, Value) and
                isinstance(signal.expr.x.expr, expr.Vec)):
            return signal.expr.x.expr.elements[index]
        else:
            return signal

    def reduce_signal_field(self, signal, is_target, name, x):
        signal = signal._auto_rewrite(
            expr.Field(name, self.reduce_signal(x, is_target=is_target)))

        if (isinstance(signal, Value) and
                isinstance(signal.expr.x, Value) and
                isinstance(signal.expr.x.expr, expr.Bundle)):
            return signal.expr.x.expr.fields[name]
        else:
            # TODO push field selection inside
            raise RuntimeError('cannot reduce bundle field selection')

    def reduce_signal_flip(self, signal, is_target, x):
        signal = signal._auto_rewrite(
            expr.Flip(self.reduce_signal(x, is_target=not is_target)))

        if (isinstance(signal, Value) and
                isinstance(signal.expr.x, Value) and
                isinstance(signal.expr.x.expr, expr.Flip)):
            return signal.expr.x.expr.x
        else:
            return signal

    def split_assignment(self, target, conditions, value):
        if self.is_valid_verilog_target(target):
            self.emit_assignment(target, conditions, value)
        elif self.split_aggregate(target, conditions, value):
            return
        elif self.split_muxes(target, conditions, value):
            return
        else:
            raise RuntimeError('cannot split assignment')
        # TODO Turn dynamic indexing into muxes

    def is_valid_verilog_target(self, target):
        # TODO Memoization
        if not self.is_valid_verilog_target_type(target.signal_type):
            return False
        return self.is_valid_verilog_target_subexpr(target)

    def is_valid_verilog_target_subexpr(self, target):
        # TODO Memoization
        if not self.is_valid_verilog_target_subexpr_type(target.signal_type):
            return False

        elif isinstance(target, StorageSignal):
            return True
        elif isinstance(target, Value):
            if isinstance(target.expr, (expr.ConstIndex, expr.ConstSlice)):
                return self.is_valid_verilog_target_subexpr(target.expr.x)

    @staticmethod
    def is_valid_verilog_target_type(signal_type):
        return isinstance(signal_type, (BoolType, BitsLike))

    def is_valid_verilog_target_subexpr_type(self, signal_type):
        while isinstance(signal_type, Vec):
            signal_type = signal_type.element_type
        return self.is_valid_verilog_target_type(signal_type)

    def split_aggregate(self, target, conditions, value):
        if isinstance(target.signal_type, Bundle):
            for field, field_type in target.signal_type.fields.items():
                subtarget = target._auto_lvalue(
                    field_type, expr.Field(field, target))
                subvalue = value._auto_lvalue(
                    field_type, expr.Field(field, value))
                self.lower_assignment(subtarget, conditions, subvalue)
        elif isinstance(target.signal_type, Vec):
            element_type = target.signal_type.element_type
            for i in range(target.signal_type.length):
                subtarget = target._auto_lvalue(
                    element_type, expr.ConstIndex(i, target))
                subvalue = value._auto_lvalue(
                    element_type, expr.ConstIndex(i, value))
                self.lower_assignment(subtarget, conditions, subvalue)
        elif isinstance(target.signal_type, BitsLike):
            if (isinstance(target, Value) and
                    isinstance(target.expr, expr.Concat)):
                pos = 0
                for field in target.expr.parts:
                    field_len = field.signal_type.width
                    subvalue = value._auto_lvalue(
                        Bits(field_len),
                        expr.ConstSlice(pos, field_len, value))
                    pos += field_len
                    self.lower_assignment(field, conditions, subvalue)
            else:
                return False
        elif isinstance(target.signal_type, Flip):
            # TODO Check if this is the right place to resolve flips
            self.lower_assignment(value.flip(), conditions, target.flip())
        else:
            return False
        return True

    @staticmethod
    def split_muxes(target, conditions, value):
        # TODO Implement
        return False

    def target_storage_signal(self, target):
        # TODO Memoize
        if isinstance(target, StorageSignal):
            return target
        elif isinstance(target, Value):
            fn = getattr(self, 'target_storage_signal_' + target.expr.fn_name)
            return fn(target, *target.expr)
        else:
            raise RuntimeError(
                'cannot determine storage signal for assignment target')

    def target_storage_signal_const_index(self, target, index, x):
        return self.target_storage_signal(x)

    def emit_assignment(self, target, conditions, value):
        target_storage = self.target_storage_signal(target)
        if isinstance(target_storage, Reg):
            clock_signal = target_storage.clk
            clock_type = clock_signal.signal_type

            positive_reset = any(
                isinstance(cond, ResetCondition) and pol
                for pol, cond in conditions)
            negative_reset = any(
                isinstance(cond, ResetCondition) and not pol
                for pol, cond in conditions)

            if positive_reset and negative_reset:
                return

            conditions = tuple(
                (pol, cond)
                for pol, cond in conditions
                if not isinstance(cond, ResetCondition))

            if clock_type.initial_reset and positive_reset:
                timing = {'mode': 'initial'}
                self.module._module_data.lowered_assignments.append(
                    (timing, target, conditions, value))

            if not clock_type.has_reset and positive_reset:
                return

            if clock_type.has_reset:
                if (negative_reset or positive_reset or
                        clock_type.has_reset == 'async'):
                    reset = self.reduce_signal(clock_signal.reset)
                    conditions = ((positive_reset, reset),) + conditions

            if clock_type.is_gated:
                ce = self.reduce_signal(clock_signal.ce)
                conditions = ((True, ce),) + conditions

            clk = self.reduce_signal(clock_signal.clk)
            timing = {'mode': 'reg', 'clk': clk}

            if clock_type.has_reset == 'async':
                timing['reset'] = reset

            self.module._module_data.lowered_assignments.append(
                (timing, target, conditions, value))
        else:
            if any(
                    isinstance(cond, ResetCondition)
                    for pol, cond in conditions):
                raise RuntimeError('Wire assignment in reset condition')
            timing = {'mode': 'wire'}
            self.module._module_data.lowered_assignments.append(
                (timing, target, conditions, value))
