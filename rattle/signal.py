import abc
from . import context
from .primitive import PrimStorage, PrimReg, PrimConst, PrimTable
from .bitvec import BitVec
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
        ctx = context.current()
        if ctx.sim_active:
            self._sim_assign(value, ctx.sim)
            return
        module_data = ctx.module._module_data
        condition = module_data.condition_stack.current_conditions()
        is_reset = module_data.condition_stack.is_reset()
        value = self.signal_type.convert(value, implicit=True)
        self._access(write=True)
        value._access(write=False)

        for key, (flip, *_) in self.signal_type._prim_shape.items():
            lvalue, rvalue = self._prims[key], value._prims[key]
            if flip:
                lvalue, rvalue = rvalue, lvalue

            lvalue.lower_and_add_to_circuit(
                condition, rvalue,
                circuit=module_data.circuit, reset=is_reset)

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

    def _sim_assign(self, value, sim_context):
        value = self.signal_type.convert(value, implicit=True)

        for key, (flip, *_) in self.signal_type._prim_shape.items():
            lvalue, rvalue = self._prims[key], value._prims[key]
            if flip:
                lvalue, rvalue = rvalue, lvalue

            sim_context._poke_prim(lvalue, rvalue)

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
        current_context = context.current()
        if current_context.sim_active:
            return current_context.sim._engine.peek(
                self._prim(key).simplify_read())

        def raise_fn(prim):
            raise ValueNotAvailable  # TODO Message

        return self._prim(key).eval(raise_fn)

    def peek(self):
        return context.current().sim.peek(self)

    @property
    def flipped(self):
        from .type import Flip
        return Flip[self]

    def _bundle_field_access(self):
        return self


_flip_dir = {'input': 'output', 'output': 'input'}


def _make_storage(signal_type, direction=None, wrap_prims=None):
    module = context.current().module
    prims = {}
    shape = signal_type._prim_shape

    flipped = _flip_dir.get(direction)

    storage = []

    for key in sorted(shape.keys()):
        flip, width, *dimensions = shape[key]

        prim = PrimStorage(
            module=module,
            width=width,
            dimensions=dimensions,
            direction=flipped if flip else direction)

        if direction is not None:
            module._module_data.io_prims.append(prim)
        module._module_data.storage_prims.append(prim)
        storage.append(prim)
        if wrap_prims is None:
            prims[key] = prim
        else:
            prims[key] = wrap_prims(module, prim)

    signal = signal_type._signal_class(signal_type, prims, storage=True)

    for prim in storage:
        prim.signal = signal

    return signal


def _make_reg(signal_type, clk=None, direction=None):
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

    def wrap_reg(module, prim):
        return PrimReg(clk_prim, en_prim, reset_prim, clock_type.reset, prim)

    return _make_storage(signal_type, direction=direction, wrap_prims=wrap_reg)


def _wrap_assign_x(module, prim):
    circuit = module._module_data.circuit

    xval = PrimConst(BitVec(prim.width, 0, -1))

    for size in prim.dimensions:
        xval = PrimTable((xval,) * size)

    prim.lower_and_add_to_circuit((), xval, circuit=circuit, reset=False)

    return prim


def Latch(signal_type):
    return _make_storage(signal_type)


def OutputLatch(signal_type):
    return _make_storage(
        signal_type, direction='output')


def Wire(signal_type):
    return _make_storage(signal_type, wrap_prims=_wrap_assign_x)


def Input(signal_type):
    return _make_storage(signal_type, direction='input')


def Output(signal_type):
    return _make_storage(
        signal_type, direction='output', wrap_prims=_wrap_assign_x)


def Reg(signal_type, clk=None):
    return _make_reg(signal_type, clk=clk)


def OutputReg(signal_type, clk=None):
    return _make_reg(signal_type, clk=clk, direction='output')


__all__ = [
    'Signal',
    'Latch',
    'OutputLatch',
    'Wire',
    'Input',
    'Output',
    'Reg',
    'OutputReg',
]
