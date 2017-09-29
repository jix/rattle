from .type import SignalType, SignalTypeMeta
from ..signal import Signal, Output
from ..slice import dispatch_getitem
from ..primitive import *


class InOutType(SignalType, metaclass=SignalTypeMeta):
    def __init__(self, width=1):
        super().__init__()
        self.__width = width

    def __repr__(self):
        return "InOutType(%r)" % self.width

    @property
    def width(self):
        return self.__width

    @property
    def _signature_tuple(self):
        return (type(self), self.width)

    @property
    def _signal_class(self):
        return InOutSignal

    @property
    def _prim_shape(self):
        return {(): ('inout', self.width)}

    def _unpack(self, unpacker):
        raise RuntimeError('cannot unpack InOut signal type')

    def _initialize_reg_value(self, reg):
        pass


class InOutSignal(Signal):
    @property
    def width(self):
        return self.signal_type.width

    def __len__(self):
        return self.width

    @property
    def value(self):
        raise RuntimeError('cannot get InOut signal value')

    def _add_to_trace(self, trace, scope, name):
        raise RuntimeError('cannot trace InOut signal value')

    def _pack(self, packer):
        raise RuntimeError('cannot pack InOut signal type')

    __getitem__ = dispatch_getitem

    def _getitem_all(self):
        return self

    def _getitem_const_index(self, index):
        return InOutType()._from_prims({
            (): PrimSlice(index, 1, self._prim())})

    def _getitem_const_slice(self, start, length):
        return InOutType(length)._from_prims({
            (): PrimSlice(start, length, self._prim())})


def InOut(width=1):
    return Output(InOutType(width))


__all__ = [
    'InOutType',
    'InOut',
]
