from .type import SignalType
from ..signal import Signal
from ..primitive import *
from ..slice import dispatch_getitem
from ..bitmath import log2up
from ..bitvec import BitVec


class Vec(SignalType):
    def __init__(self, length, element_type):
        super().__init__()
        self.__element_type = element_type
        self.__length = length

    @property
    def element_type(self):
        return self.__element_type

    @property
    def length(self):
        return self.__length

    def __repr__(self):
        return "Vec(%i, %r)" % (self.length, self.element_type)

    def short_repr(self):
        return "Vec(%i, %s)" % (self.length, self.element_type.short_repr())

    @property
    def _signature_tuple(self):
        return (type(self), self.length, self.element_type)

    def _const_signal(self, value, *, implicit):
        if isinstance(value, VecHelper):
            value = value._values

        if isinstance(value, (list, tuple)):
            # TODO Check length
            transposed = {k: [] for k in self._prim_shape}

            for element in value:
                element = self.element_type.convert(element, implicit=implicit)
                for field, prim in element._prims.items():
                    transposed[field].append(prim)

            return self._from_prims({
                k: PrimTable(v) for k, v in transposed.items()})
        return super()._const_signal(value, implicit=implicit)

    @property
    def _signal_class(self):
        return VecSignal

    @property
    def _prim_shape(self):
        return {
            k: v + (self.length,)
            for k, v in self.element_type._prim_shape.items()}


class VecSignal(Signal):
    @property
    def element_type(self):
        return self.signal_type.element_type

    def __len__(self):
        return self.signal_type.length

    __getitem__ = dispatch_getitem

    def _getitem_all(self):
        return self

    def _getitem_const_index(self, index):
        index_width = log2up(len(self))
        return self._getitem_prim(PrimConst(BitVec(index_width, index)))

    def _getitem_dynamic_index(self, index):
        return self._getitem_prim(index._prim())

    def _getitem_prim(self, index_prim):
        return self.element_type._from_prims({
            k: PrimIndex(index_prim, v)
            for k, v in self._prims.items()})

    def _getitem_const_slice(self, start, length):
        return Vec(length, self.element_type)[
            [self[i] for i in range(start, start + length)]]

    @property
    def value(self):
        return tuple(self[i].value for i in range(len(self)))

    def _add_to_trace(self, trace, scope, name):
        for i in range(self.signal_type.length):
            self[i]._add_to_trace(trace, scope + [('struct', name)], str(i))


class VecHelper:
    def __init__(self, values):
        self._values = values

    def __repr__(self):
        return 'vec(%s)' % ', '.join(map(repr, self._values))

    # TODO Partial Vec API


def vec(*args):
    if args and all(isinstance(signal, Signal) for signal in args):
        common_type = SignalType.common(signal.signal_type for signal in args)
        return Vec(len(args), common_type)[args]
    return VecHelper(args)
