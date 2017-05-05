from .type import SignalType
from ..signal import Signal


class InOut(SignalType):
    def __init__(self, contained_type):
        super().__init__()
        self.__contained_type = contained_type

    def __repr__(self):
        return "InOut(%r)" % self.contained_type

    @property
    def contained_type(self):
        return self.__contained_type

    @property
    def _signature_tuple(self):
        return (type(self), self.contained_type)

    @property
    def _signal_class(self):
        return InOutSignal

    @property
    def _prim_shape(self):
        return {
            key: ('inout', *shape)
            for key, (flipped, *shape)
            in self.contained_type._prim_shape.items()}

    def _unpack(self, unpacker):
        raise RuntimeError('cannot unpack InOut signal type')


class InOutSignal(Signal):
    @property
    def value(self):
        raise RuntimeError('cannot get InOut signal value')

    def _add_to_trace(self, trace, scope, name):
        raise RuntimeError('cannot trace InOut signal value')

    def _pack(self, packer):
        raise RuntimeError('cannot pack InOut signal type')
