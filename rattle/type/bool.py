from .type import *

from .. import expr
from ..signal import Value, Const
from ..bitvec import bv, ubool


class BoolType(SignalType):
    def __repr__(self):
        return "Bool"

    @property
    def _signature_tuple(self):
        return (type(self),)

    def _const_signal(self, value, *, implicit):
        # pylint: disable=unused-variable
        return Const(Bool, bv(ubool(value)))


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

    def repeat(self, count):
        from .bits import Bits
        if not isinstance(count, int):
            raise TypeError('repetition count must be an integer')
        elif count < 0:
            raise ValueError('repitition count must not be negative')
        else:
            self._access_read()
            return Value._auto(Bits(count), expr.Repeat(count, self))

    @property
    def value(self):
        return self.raw_value[0]

BoolType.signal_mixin = BoolMixin
