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
            if signal_type.width >= self.width:
                return self.extend(signal_type.width).as_bits()
        return super()._convert(signal_type, implicit=implicit)

    def _generic_convert(self, signal_type_class, *, implicit):
        if signal_type_class == Bits:
            return self.as_bits()
        return super()._convert(signal_type_class, implicit=implicit)

    def as_bits(self):
        return self._auto_lvalue(Bits(self.width), expr.Nop(self))

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
            if self.width >= signal.width:
                return signal.extend(self.width).as_uint()
        return super()._convert(signal, implicit=implicit)

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.as_uint()
        return super()._generic_convert(signal, implicit=implicit)


class UIntMixin(IntMixin):
    def _convert(self, signal_type, *, implicit):
        if signal_type.__class__ == SInt:
            if signal_type.width >= self.width + 1:
                return self.extend(signal_type.width).as_bits().as_sint()
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

    def _convert(self, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            if self.width >= signal.width:
                return signal.extend(self.width).as_sint()
        return super()._convert(signal, implicit=implicit)

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.as_sint()
        return super()._generic_convert(signal, implicit=implicit)


class SIntMixin(IntMixin):
    def _extend_unchecked(self, width):
        self._access_read()
        return Value._auto(SInt(width), expr.SignExt(width, self))

    @property
    def value(self):
        if self.raw_value.mask == 0:
            return signext(self.raw_value.width, self.raw_value.value)
        else:
            return Unk

SInt.signal_mixin = SIntMixin
