import abc
from . import context
from .primitive import PrimStorage, PrimReg
from .error import (
    ValueNotAvailable, InvalidSignalRead, InvalidSignalAssignment)


class Signal(metaclass=abc.ABCMeta):
    @classmethod
    def _from_prims(cls, signal_type, prims):
        return cls(signal_type, prims)

    def __init__(self, signal_type, prims, storage=False):
        self._signal_type = signal_type
        assert len(signal_type._prim_shape) == len(prims)
        assert all(
            prims[k].shape == v[1:]
            for k, v in signal_type._prim_shape.items())
        self._prims = prims
        self._storage = storage

    @property
    def signal_type(self):
        return self._signal_type

    def assign(self, value):
        module = context.current().module
        condition_stack = module._module_data.condition_stack
        value = self.signal_type.convert(value, implicit=True)
        self._access(write=True)
        value._access(write=False)

        for key, (flip, *_) in self.signal_type._prim_shape.items():
            target, source = self._prims[key], value._prims[key]
            if flip:
                target, source = source, target

            priority, condition = condition_stack.current_conditions()

            module._module_data.assignments.append(
                (target, priority, condition, source))

    def _access(self, write=False):
        module = context.current().module
        for key, (flip, *_) in self.signal_type._prim_shape.items():
            prim = self._prims[key]

            write_prim = write ^ flip

            if write_prim:
                if module not in prim.allowed_writers:
                    raise InvalidSignalAssignment  # TODO Message
            else:
                if module not in prim.allowed_readers:
                    raise InvalidSignalRead  # TODO Message

    def __setitem__(self, key, value):
        if key == slice(None, None, None):
            self.assign(value)
        else:
            raise TypeError('Signal object does not support item assignment')

    def __getitem__(self, key):
        if key == slice(None, None, None):
            return self
        else:
            raise TypeError('Signal object is not subscriptable')

    def _convert(self, signal_type, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        return NotImplemented

    def _generic_convert(self, signal_type_class, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        return NotImplemented

    def _const_signal(self, signal_type, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        return NotImplemented

    def _generic_const_signal(self, signal_type_class, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        return NotImplemented

    def as_implicit(self, name):
        from .implicit import Implicit
        Implicit._module_scope_bind(name, self)
        return self

    def __hash__(self):
        raise TypeError("signals are not hashable")

    @abc.abstractproperty
    def value(self):
        pass

    def _prim(self, key=()):
        return self._prims[key]

    def _prim_value(self, key=()):
        def raise_fn(prim):
            raise ValueNotAvailable  # TODO Message

        return self._prim(key).eval(raise_fn)


_flip_dir = {'input': 'output', 'output': 'input'}


def _make_storage(signal_type, direction=None, wrap_prims=lambda x: x):
    module = context.current().module
    prims = {}
    shape = signal_type._prim_shape

    flipped = _flip_dir.get(direction)

    for key in sorted(shape.keys()):
        flip, width, *dimensions = shape[key]

        prims[key] = wrap_prims(PrimStorage(
            module=module,
            width=width,
            dimensions=dimensions,
            direction=flipped if flip else direction))

    return signal_type._signal_class(signal_type, prims, storage=True)


def Wire(signal_type):
    return _make_storage(signal_type)


def Input(signal_type):
    return _make_storage(signal_type, direction='input')


def Output(signal_type):
    return _make_storage(signal_type, direction='output')


def Reg(signal_type, clk=None):
    from .type.clock import Clock
    from .implicit import Implicit

    if clk is None:
        clk = Implicit('clk')

    clock_type = clk.signal_type

    if not isinstance(clock_type, Clock):
        raise TypeError('clk must be of signal type Clock')

    clk._access()

    clk_prim = clk.clk._prim()
    if clock_type.reset not in ('init', False):
        reset_prim = clk.reset._prim()
    else:
        reset_prim = None
    if clock_type.gated:
        en_prim = clk.en._prim()
    else:
        en_prim = None

    def wrap_reg(prim):
        return PrimReg(clk_prim, en_prim, reset_prim, clock_type.reset, prim)

    signal = _make_storage(signal_type, wrap_prims=wrap_reg)
    return signal
