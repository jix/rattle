from .type import *

from .. import expr
from ..signal import Value, Const


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
    def __invert__(self):
        self._access_read()
        return Value(Bool, expr.Not(self))

BoolType.signal_mixin = BoolMixin


class BoolConstMixin(Const, BoolMixin):
    def __invert__(self):
        return Const(Bool, not self.value)

BoolType.const_mixin = BoolConstMixin
