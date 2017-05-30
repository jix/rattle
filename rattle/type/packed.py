from .type import SignalType
from ..signal import Signal
from ..error import ConversionNotImplemented
from ..bitvec import X


class Packed(SignalType):
    def __init__(self, unpacked_type):
        super().__init__()
        self.__unpacked_type = unpacked_type

        self._packed_type = unpacked_type[X].packed.signal_type

    def __repr__(self):
        return "Packed(%r)" % self.__unpacked_type

    @property
    def unpacked_type(self):
        return self.__unpacked_type

    @property
    def _signature_tuple(self):
        return (type(self), self.__unpacked_type)

    @property
    def _signal_class(self):
        return PackedSignal

    @property
    def _prim_shape(self):
        return self._packed_type._prim_shape

    def _convert(self, signal, *, implicit):
        try:
            signal = self.__unpacked_type.convert(signal, implicit=implicit)
        except ConversionNotImplemented:
            return super()._convert(signal, implicit=implicit)

        return self._from_prims(signal.packed._prims)

    def _const_signal(self, value, *, implicit):
        try:
            signal = self.__unpacked_type.convert(value, implicit=implicit)
        except ConversionNotImplemented:
            return super()._const_signal(signal, implicit=implicit)

        return self._from_prims(signal.packed._prims)

    def _unpack(self, unpacker):
        self._from_prims(self.__packed_type._unpack(unpacker)._prims)

    def _initialize_reg_value(self, reg):
        self.unpacked_type.initial_reg_value(reg.unpacked)


class PackedSignal(Signal):
    @property
    def value(self):
        return self.unpacked.value

    def _convert(self, signal_type, *, implicit):
        if signal_type == self.signal_type.unpacked_type:
            return self.unpacked
        else:
            return super()._convert(signal_type, implicit=implicit)

    @property
    def packed(self):
        return self.signal_type._packed_type._from_prims(self._prims)

    @property
    def unpacked(self):
        return self.signal_type.unpacked_type.unpack(self.packed)

    def _add_to_trace(self, trace, scope, name):
        self.packed._add_to_trace(
            trace, scope + [('struct', name)], 'packed')
        self.unpacked._add_to_trace(
            trace, scope + [('struct', name)], 'unpacked')

    def _pack(self, packer):
        self.packed._pack(packer)
