from contextlib import contextmanager
from ..type import BitsLike, BoolType, Vec, Bundle, Flip
from ..signal import Value, Wire, Input, Output, IOPort
from ..reg import Reg
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

        for submodule in self.module._module_data.submodules:
            Lower(submodule, settings=settings)

        with self.module.reopen():
            # TODO Generate proxy Wires for named Values
            self.lower_storage_signals()

    def lower_storage_signals(self):
        for signal in list(self.module._module_data.storage_signals):
            self.lower_signal(signal)

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
