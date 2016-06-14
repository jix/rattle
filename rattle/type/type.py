import abc

from ..signal import Signal, Const


class SignalType(metaclass=abc.ABCMeta):
    def __getitem__(self, key):
        return Const(self, key)

    @property
    def signal_mixin(self):
        return SignalMixin

    @property
    def const_mixin(self):
        return self.signal_mixin


class SignalMixin(Signal):
    pass
