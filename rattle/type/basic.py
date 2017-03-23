import abc

from ..signal import Signal
from .type import SignalType, SignalTypeMeta


class BasicType(SignalType, metaclass=SignalTypeMeta):
    @property
    def _prim_shape(self):
        return {(): (False, self._prim_width,)}

    @abc.abstractproperty
    def _prim_width(self):
        pass

    def _from_prim(self, prim):
        return self._from_prims({(): prim})

    def _unpack(self, unpacker):
        return self._from_prim(unpacker.unpack(self._prim_width)._prim())


class BasicSignal(Signal, metaclass=abc.ABCMeta):
    # pylint: disable=abstract-method
    def _add_to_trace(self, trace, scope, name):
        trace._add_prim(scope, name, self._prim())

    def _pack(self, packer):
        from .bits import Bits
        packer.pack(
            Bits(self.signal_type._prim_width)._from_prim(self._prim()))
