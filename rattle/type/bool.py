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

    @staticmethod
    def _eval_and(a, b):
        for (x, y) in ((a, b), (b, a)):
            if isinstance(x, Const):
                if x.value:
                    return y
                else:
                    return Bool[False]

    @staticmethod
    def _eval_or(a, b):
        for (x, y) in ((a, b), (b, a)):
            if isinstance(x, Const):
                if x.value:
                    return Bool[True]
                else:
                    return y

    @staticmethod
    def _eval_xor(a, b):
        if all(isinstance(x, Const) for x in (a, b)):
            return Bool[a.value ^ b.value]

    @staticmethod
    def _eval_not(x):
        if isinstance(x, Const):
            return Bool[not x.value]

Bool = BoolType()
BoolType.__new__ = lambda cls: Bool


class BoolMixin(SignalMixin):
    def __invert__(self):
        self._access_read()
        return Value._auto(Bool, expr.Not(self))

    def _binary_bitop(self, other, op):
        try:
            other = self.signal_type.convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        self._access_read()
        other._access_read()
        return Value._auto(Bool, op(self, other))

    def __and__(self, other):
        return self._binary_bitop(other, expr.And)

    def __rand__(self, other):
        return self.__and__(other)

    def __or__(self, other):
        return self._binary_bitop(other, expr.Or)

    def __ror__(self, other):
        return self.__or__(other)

    def __xor__(self, other):
        return self._binary_bitop(other, expr.Xor)

    def __rxor__(self, other):
        return self.__xor__(other)

BoolType.signal_mixin = BoolMixin
