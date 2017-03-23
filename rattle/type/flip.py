from .type import SignalType, SignalTypeMeta
from ..signal import Signal


class FlipMeta(SignalTypeMeta):
    def __call__(cls, unflipped_type):
        if isinstance(unflipped_type, Flip):
            return unflipped_type.unflipped_type
        return super().__call__(unflipped_type)


class Flip(SignalType, metaclass=FlipMeta):
    def __init__(self, unflipped_type):
        super().__init__()
        self.__unflipped_type = unflipped_type

    def __repr__(self):
        return "Flip(%r)" % self.unflipped_type

    @property
    def unflipped_type(self):
        return self.__unflipped_type

    @property
    def _signature_tuple(self):
        return (type(self), self.unflipped_type)

    @property
    def _signal_class(self):
        return FlipSignal

    @property
    def _prim_shape(self):
        return {
            key: (not flipped, *shape)
            for key, (flipped, *shape)
            in self.unflipped_type._prim_shape.items()}

    def _convert(self, signal, *, implicit):
        if not implicit:
            if signal.signal_type == self.unflipped_type:
                return Flip[signal]
        return super()._convert(signal, implicit=implicit)

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        if not implicit:
            return cls(signal.signal_type)._from_prims(signal._prims)

        return super()._generic_convert(signal, implicit=implicit)

    def _unpack(self, unpacker):
        with unpacker.flip():
            return self.unflipped_type._unpack(unpacker)


class FlipSignal(Signal):
    def value(self):
        return self.flip().value

    @property
    def flipped(self):
        return self.signal_type.unflipped_type._from_prims(self._prims)

    def _bundle_field_access(self):
        return self.flipped

    def _add_to_trace(self, trace, scope, name):
        self.flipped._add_to_trace(trace, scope, name)

    def _pack(self, packer):
        with packer.flip():
            self.flipped._pack(packer)
