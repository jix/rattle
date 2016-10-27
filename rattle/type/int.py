import abc

from .type import *
from .bits import *
from ..bitvec import X
from ..bitmath import signext


class Int(BitsLike, metaclass=SignalMeta):
    @abc.abstractproperty
    def signed(self):
        pass

    @classmethod
    def _generic_const_signal(cls, value, *, implicit):
        if isinstance(value, int):
            if value < 0:
                return SInt[value]
            else:
                return UInt[value]
        else:
            return super()._generic_const_signal(value, implicit=implicit)

    @staticmethod
    def from_value_range(min_value, max_value):
        width = max_value.bit_length()
        if min_value < 0:
            width = max(width, (~min_value).bit_length()) + 1
            return SInt(width)
        else:
            return UInt(width)

    def __or__(self, other):
        if isinstance(other, Int):
            return Int.from_value_range(
                min(self.min_value, other.min_value),
                max(self.max_value, other.max_value))
        else:
            return NotImplemented


class IntMixin(BitsLikeMixin):
    def _convert(self, signal_type, *, implicit):
        if signal_type.__class__ == Bits:
            return self.resize(signal_type.width).as_bits()
        return super()._convert(signal_type, implicit=implicit)

    def _generic_convert(self, signal_type_class, *, implicit):
        if signal_type_class == Bits:
            return self.as_bits()
        elif signal_type_class == Int:
            return self
        return super()._generic_convert(signal_type_class, implicit=implicit)

    def as_bits(self):
        return self._auto_lvalue(Bits(self.width), expr.Nop(self))

    def __and__(self, other):
        try:
            other = Int.generic_convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        a, b = self, other
        if a.signal_type.signed & b.signal_type.signed:
            result_type = SInt
            result_width = max(a.width, b.width)
        else:
            result_type = UInt

        if a.signal_type.signed:
            result_width = b.width
        elif b.signal_type.signed:
            result_width = a.width
        else:
            result_width = min(a.width, b.width)
        a, b = a.resize(result_width), b.resize(result_width)
        a._access_read()
        b._access_read()
        return Value._auto(result_type(result_width), expr.And(a, b))

    def _binary_bitop(self, other, op):
        try:
            other = Int.generic_convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        a, b = self, other
        if a.signal_type.signed & b.signal_type.signed:
            result_type = SInt
            result_width = max(a.width, b.width)
        elif a.signal_type.signed | b.signal_type.signed:
            result_type = SInt
            result_width = max(
                a.width + b.signal_type.signed, b.width + a.signal_type.signed)
        else:
            result_type = UInt
            result_width = max(a.width, b.width)
        a, b = a.extend(result_width), b.extend(result_width)
        a._access_read()
        b._access_read()
        return Value._auto(result_type(result_width), op(a, b))

    def __add__(self, other):
        try:
            other = Int.generic_convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        a, b = self, other
        result_type = Int.from_value_range(
            a.signal_type.min_value + b.signal_type.min_value,
            a.signal_type.max_value + b.signal_type.max_value)
        result_width = result_type.width
        a, b = a.extend(result_width), b.extend(result_width)
        a._access_read()
        b._access_read()
        return Value._auto(result_type, expr.Add(a, b))

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        try:
            other = Int.generic_convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        a, b = self, other
        result_type = Int.from_value_range(
            a.signal_type.min_value - b.signal_type.max_value,
            a.signal_type.max_value - b.signal_type.min_value)
        result_width = result_type.width
        a, b = a.extend(result_width), b.extend(result_width)
        a._access_read()
        b._access_read()
        return Value._auto(result_type, expr.Sub(a, b))

    def __rsub__(self, other):
        try:
            other = Int.generic_convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        return other - self

    def __mul__(self, other):
        try:
            other = Int.generic_convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        a, b = self, other
        result_type = Int.from_value_range(
            min(
                a.signal_type.min_value * b.signal_type.max_value,
                a.signal_type.max_value * b.signal_type.min_value),
            max(
                a.signal_type.min_value * b.signal_type.min_value,
                a.signal_type.max_value * b.signal_type.max_value))
        result_width = result_type.width
        if result_width == 0:
            return UInt(0)[0]
        a, b = a.resize(result_width), b.resize(result_width)
        a._access_read()
        b._access_read()
        return Value._auto(result_type, expr.Mul(a, b))

    def __rmul__(self, other):
        return self * other

    def __neg__(self):
        return 0 - self

Int.signal_mixin = IntMixin


class UInt(Int):
    @property
    def signed(self):
        return False

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return (1 << self.width) - 1

    @classmethod
    def _generic_const_signal(cls, value, *, implicit):
        # pylint: disable=bad-super-call
        # We intentionally skip the Int version as it will call this one
        return super(Int, cls)._generic_const_signal(value, implicit=implicit)

    def _convert(self, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.resize(self.width).as_uint()
        return super()._convert(signal, implicit=implicit)

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.as_uint()
        return super()._generic_convert(signal, implicit=implicit)


class UIntMixin(IntMixin):
    def _convert(self, signal_type, *, implicit):
        if signal_type.__class__ == SInt:
            return self.resize(signal_type.width).as_bits().as_sint()
        elif signal_type.__class__ == UInt:
            return self.resize(signal_type.width)
        return super()._convert(signal_type, implicit=implicit)

    def _generic_convert(self, signal_type_class, *, implicit):
        if signal_type_class == SInt:
            return self.as_sint()
        return super()._generic_convert(signal_type_class, implicit=implicit)

    def as_sint(self):
        return self.extend(self.width + 1).as_bits().as_sint()

    def _extend_unchecked(self, width):
        self._access_read()
        return Value._auto(UInt(width), expr.ZeroExt(width, self))

    def _truncate_unchecked(self, width):
        return self._auto_lvalue(UInt(width), expr.ConstSlice(0, width, self))

    def __invert__(self):
        return ~self.as_sint()

    @property
    def value(self):
        if self.raw_value.mask == 0:
            return self.raw_value.value
        else:
            return X

UInt.signal_mixin = UIntMixin


class SInt(Int):
    def __init__(self, width):
        super().__init__(width)
        if width < 1:
            raise ValueError('the width of a signed integer must be positive')

    @property
    def signed(self):
        return True

    @property
    def min_value(self):
        return -(1 << (self.width - 1))

    @property
    def max_value(self):
        return (1 << (self.width - 1)) - 1

    @classmethod
    def _generic_const_signal(cls, value, *, implicit):
        if isinstance(value, int):
            if value < 0:
                width = (~value).bit_length() + 1
            else:
                width = value.bit_length() + 1
            return Const(cls(width), BitVec(width, value))
        else:
            return super()._generic_const_signal(value, implicit=implicit)

    def _const_signal(self, value, *, implicit):
        if isinstance(value, int):
            return SInt[value].extend(self.width)
        else:
            return super()._const_signal(value, implicit=implicit)

    def _convert(self, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.resize(self.width).as_sint()
        return super()._convert(signal, implicit=implicit)

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.as_sint()
        return super()._generic_convert(signal, implicit=implicit)


class SIntMixin(IntMixin):
    def _convert(self, signal_type, *, implicit):
        if signal_type.__class__ == UInt:
            return self.resize(signal_type.width).as_bits().as_uint()
        elif signal_type.__class__ == SInt:
            return self.resize(signal_type.width)
        return super()._convert(signal_type, implicit=implicit)

    def _extend_unchecked(self, width):
        self._access_read()
        return Value._auto(SInt(width), expr.SignExt(width, self))

    def _truncate_unchecked(self, width):
        return self._auto_lvalue(SInt(width), expr.ConstSlice(0, width, self))

    @property
    def value(self):
        if self.raw_value.mask == 0:
            return signext(self.raw_value.width, self.raw_value.value)
        else:
            return X

SInt.signal_mixin = SIntMixin
