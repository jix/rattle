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

    def _binary_bitop(self, other, op, const_op):
        try:
            other = self.signal_type.convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        self._access_read()
        other._access_read()
        if isinstance(self, Const) and isinstance(other, Const):
            return Bool[const_op(self.value, other.value)]
        else:
            return Value(Bool, op(self, other))

    def __and__(self, other):
        return self._binary_bitop(other, expr.And, lambda a, b: a & b)

    def __rand__(self, other):
        return self.__and__(other)

    def __or__(self, other):
        return self._binary_bitop(other, expr.Or, lambda a, b: a | b)

    def __ror__(self, other):
        return self.__or__(other)

    def __xor__(self, other):
        return self._binary_bitop(other, expr.Xor, lambda a, b: a ^ b)

    def __rxor__(self, other):
        return self.__xor__(other)

BoolType.signal_mixin = BoolMixin


class BoolConstMixin(Const, BoolMixin):
    def __invert__(self):
        return Const(Bool, not self.value)

BoolType.const_mixin = BoolConstMixin
