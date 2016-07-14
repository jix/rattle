from .type import *
from ..signal import Const


class BoolType(SignalType):
    def __repr__(self):
        return "Bool"

    @property
    def _signature_tuple(self):
        return (type(self),)

    def _const_signal(self, value):
        return Const(Bool, bool(value))


Bool = BoolType()
BoolType.__new__ = lambda cls: Bool


class BoolMixin(SignalMixin):
    pass

BoolType.signal_mixin = BoolMixin


class BoolConstMixin(Const, BoolMixin):
    pass

BoolType.const_mixin = BoolConstMixin
