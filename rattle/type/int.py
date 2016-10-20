import abc

from .type import *
from .bits import *
from ..bitvec import Unk
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


class IntMixin(BitsLikeMixin):
    def _convert(self, signal_type, *, implicit):
        if signal_type.__class__ == Bits:
            return self.resize(signal_type.width).as_bits()
        return super()._convert(signal_type, implicit=implicit)

    def _generic_convert(self, signal_type_class, *, implicit):
        if signal_type_class == Bits:
            return self.as_bits()
        return super()._convert(signal_type_class, implicit=implicit)

    def as_bits(self):
        return self._auto_lvalue(Bits(self.width), expr.Nop(self))

    def __and__(self, other):
        if not isinstance(other.signal_type, Int):
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
        if not isinstance(other.signal_type, Int):
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


Int.signal_mixin = IntMixin


class UInt(Int):
    @property
    def signed(self):
        return False

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
        return super()._convert(signal_type_class, implicit=implicit)

    def as_sint(self):
        return self.extend(self.width + 1).as_bits().as_sint()

    def _extend_unchecked(self, width):
        self._access_read()
        return Value._auto(UInt(width), expr.ZeroExt(width, self))

    def _truncate_unchecked(self, width):
        return self._auto_lvalue(UInt(width), expr.ConstSlice(0, width, self))

    @property
    def value(self):
        if self.raw_value.mask == 0:
            return self.raw_value.value
        else:
            return Unk

UInt.signal_mixin = UIntMixin


class SInt(Int):
    def __init__(self, width):
        super().__init__(width)
        if width < 1:
            raise ValueError('the width of a signed integer must be positive')

    @property
    def signed(self):
        return True

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
            return Unk

SInt.signal_mixin = SIntMixin
