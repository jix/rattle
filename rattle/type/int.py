"""Fixed width integers."""
import abc

from .type import SignalTypeMeta
from .bits import Bits, BitsLike, BitsLikeSignal
from ..signal import Signal
from ..primitive import *
from ..bitvec import BitVec, X
from ..bitmath import bitmask, signext
from ..error import ConversionNotImplemented


class Int(BitsLike, metaclass=SignalTypeMeta):
    """Fixed-width integers.

    Abstract superclass of :class:`UInt` and :class:`SInt`.
    Subclass of :class:`BitsLike`.
    """

    @abc.abstractproperty
    def signed(self):
        """Whether the MSB is interpreted as a sign bit."""
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

    @abc.abstractproperty
    def min_value(self):
        """Smallest representable value."""
        pass

    @abc.abstractproperty
    def max_value(self):
        """Largest representable value."""
        pass

    @staticmethod
    def from_value_range(min_value, max_value):
        """Return a signal type that can represent a given range.

        Args:
            min_value (int): Smallest value required to be representable.
            max_value (int): Largest value required to be representable.

        Returns:
            SignalType: An UInt or SInt of appropriate width.
        """
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


class IntSignal(BitsLikeSignal):
    """Fixed-width integer signal.

    Inherits operations from :class:`rattle.type.bits.BitsLikeSignal`.
    This also provides the following operations using Python operators:

    *   Arithmetic (except devision).
    *   Integer comparison, supports mixing SInt and UInt types.
    """
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
        """Convert into a Bits signal of the same width."""
        return Bits(self.width)._from_prim(self._prim())

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
        return result_type(result_width)._from_prim(
            PrimAnd(a._prim(), b._prim()))

    def _binary_bitop(self, other, op, result_override=None, signed_op=None):
        # pylint: disable=arguments-differ
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

        if signed_op is not None and result_type(result_width).signed:
            op = signed_op

        if result_override is None:
            result_type = result_type(result_width)
        else:
            result_type = result_override

        return result_type._from_prim(op(a._prim(), b._prim()))

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
        return result_type._from_prim(
            PrimAdd(a._prim(), b._prim()))

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
        return result_type._from_prim(
            PrimSub(a._prim(), b._prim()))

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
        return result_type._from_prim(
            PrimMul(a._prim(), b._prim()))

    def __rmul__(self, other):
        return self * other

    def __neg__(self):
        return 0 - self

    def __eq__(self, other):
        from .bool import Bool
        return self._binary_bitop(other, PrimEq, result_override=Bool)

    def __lt__(self, other):
        from .bool import Bool
        return self._binary_bitop(
            other, PrimLt, result_override=Bool, signed_op=PrimSignedLt)

    def __le__(self, other):
        return ~(self > other)

    def __gt__(self, other):
        try:
            other = Int.generic_convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        return other < self

    def __ge__(self, other):
        return ~(self < other)

    def __lshift__(self, shift):
        if isinstance(shift, int):
            if shift < 0:
                raise ValueError('negative shift count')

            return type(self.signal_type)(self.width + shift)._from_prim(
                PrimConcat([PrimConst(BitVec(shift, 0)), self._prim()]))
        else:
            try:
                shift = UInt.generic_convert(shift, implicit=True)
            except ConversionNotImplemented:
                return NotImplemented

            if shift.width > 16:
                # This is sadly needed to avoid memory explosion for
                # intermediate values
                raise RuntimeError(
                    'excessive shift amount width, '
                    'use Bits to generate truncated shifts')

            output_width = self.width + bitmask(shift.width)

            return type(self.signal_type).generic_convert(
                self.extend(output_width).as_bits() << shift)

    def __rshift__(self, shift):
        if isinstance(shift, int):
            if shift < 0:
                raise ValueError('negative shift count')

            shift = min(shift, self.width - self.signal_type.signed)

            return type(self.signal_type)(self.width - shift)._from_prim(
                PrimSlice(shift, self.width - shift, self._prim()))
        else:
            try:
                shift = UInt.generic_convert(shift, implicit=True)
            except ConversionNotImplemented:
                return NotImplemented

            return self.signal_type._from_prim(
                self._rshift_op(self._prim(), shift._prim()))

    @abc.abstractproperty
    def _rshift_op(self):
        pass


class UInt(Int):
    """Fixed-width unsigned integer signal type."""
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
        result = super(Int, cls)._generic_const_signal(
            value, implicit=implicit)
        if Signal.isinstance(result, Bits):
            result = result.as_uint()
        return result

    def _const_signal(self, value, *, implicit):
        result = super()._const_signal(value, implicit=implicit)
        if Signal.isinstance(result, Bits):
            result = result.as_uint()
        return result

    def _convert(self, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.resize(self.width).as_uint()
        return super()._convert(signal, implicit=implicit)

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.as_uint()
        return super()._generic_convert(signal, implicit=implicit)

    @property
    def _signal_class(self):
        return UIntSignal


class UIntSignal(IntSignal):
    """Fixed-width unsigned integer signal."""
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

    def as_uint(self):
        return self

    def _extend_unchecked(self, width):
        return UInt(width)._from_prim(
            PrimZeroExt(width, self._prim()))

    def _truncate_unchecked(self, width):
        return UInt(width)._from_prim(
            PrimSlice(0, width, self._prim()))

    def __invert__(self):
        return (~self.extend(self.width + 1).as_bits()).as_sint()

    @property
    def _rshift_op(self):
        return PrimShiftRight

    @property
    def value(self):
        value = self._prim_value()
        if value.mask == 0:
            return value.value
        elif value.mask == bitmask(self.width):
            return X
        else:
            return value


class SInt(Int):
    """Fixed-width signed integer signal type."""
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
            return SInt(width)._from_prim(
                PrimConst(BitVec(width, value)))
        else:
            result = super()._generic_const_signal(value, implicit=implicit)
            if Signal.isinstance(result, Bits):
                result = result.as_sint()
            return result

    def _const_signal(self, value, *, implicit):
        if isinstance(value, int):
            return SInt[value].extend(self.width)
        else:
            result = super()._const_signal(value, implicit=implicit)
            if Signal.isinstance(result, Bits):
                result = result.as_sint()
            return result

    def _convert(self, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.resize(self.width).as_sint()
        return super()._convert(signal, implicit=implicit)

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        if not implicit and signal.signal_type.__class__ == Bits:
            return signal.as_sint()
        return super()._generic_convert(signal, implicit=implicit)

    @property
    def _signal_class(self):
        return SIntSignal


class SIntSignal(IntSignal):
    """Fixed-width signed integer signal."""
    def _convert(self, signal_type, *, implicit):
        if signal_type.__class__ == UInt:
            return self.resize(signal_type.width).as_bits().as_uint()
        elif signal_type.__class__ == SInt:
            return self.resize(signal_type.width)
        return super()._convert(signal_type, implicit=implicit)

    def as_sint(self):
        return self

    def _extend_unchecked(self, width):
        return SInt(width)._from_prim(
            PrimSignExt(width, self._prim()))

    def _truncate_unchecked(self, width):
        return SInt(width)._from_prim(
            PrimSlice(0, width, self._prim()))

    def __invert__(self):
        return super().__invert__().as_sint()

    @property
    def _rshift_op(self):
        return PrimArithShiftRight

    @property
    def value(self):
        value = self._prim_value()
        if value.mask == 0:
            return signext(value.width, value.value)
        elif value.mask == bitmask(self.width):
            return X
        else:
            return value
