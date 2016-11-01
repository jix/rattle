from .type import *
from .. import expr
from ..signal import Value, Const
from ..error import ConversionNotImplemented
from ..bitvec import BitVec, bv
from ..slice import check_slice


class BitsLike(SignalType, metaclass=SignalMeta):
    def __init__(self, width):
        super().__init__()
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        if width < 0:
            raise ValueError('signal width must be non-negative ')
        self.__width = width

    @property
    def width(self):
        return self.__width

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.width)

    @property
    def _signature_tuple(self):
        return (type(self), self.width)

    @classmethod
    def concat(cls, *signals):
        # TODO Document lsb first order
        # TODO Check for / coerce into Bits type
        return Value._auto_concat_lvalue(
            signals, cls(sum(signal.width for signal in signals)),
            expr.Concat(signals))

    @classmethod
    def _generic_const_signal(cls, value, *, implicit):
        if isinstance(value, int):
            if value < 0:
                raise ValueError(
                    "cannot convert negative value to %s" % cls.__name__)
            width = value.bit_length()
            value = BitVec(width, value)
        elif isinstance(value, str):
            value = bv(value)

        if isinstance(value, BitVec):
            return Const(cls(value.width), value)
        else:
            return super()._generic_const_signal(value, implicit=implicit)

    def _const_signal(self, value, *, implicit):
        if isinstance(value, int):
            if value < 0:
                raise ValueError(
                    "cannot convert negative value to %s" % self)
            width = value.bit_length()
            if width > self.width:
                raise ValueError(
                    "constant too large for %r" % self)
            value = BitVec(self.width, value)
        elif isinstance(value, str):
            value = bv(value)
        if isinstance(value, BitVec):
            if value.width != self.width:
                raise ValueError(
                    "constant of wrong size (%i) for %r" % (value.width, self))
            return Const(self, value)
        else:
            return super()._const_signal(value, implicit=implicit)


class BitsLikeMixin(SignalMixin):
    @property
    def width(self):
        return self.signal_type.width

    def concat(self, *others):
        return Bits.concat(self, *others)

    def __matmul__(self, other):
        # TODO Document msb first order for @ operator
        return Bits.concat(other, self)

    def __invert__(self):
        self._access_read()
        return Value._auto(self.signal_type, expr.Not(self))

    def _binary_bitop(self, other, op):
        if other.signal_type == self.signal_type:
            self._access_read()
            other._access_read()
            return Value._auto(self.signal_type, op(self, other))
        else:
            return NotImplemented

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

    def extend(self, width):
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        if width < self.width:
            raise ValueError('extended width less than input width')
        elif width == self.width:
            return self
        else:
            return self._extend_unchecked(width)

    def truncate(self, width):
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        if width > self.width:
            raise ValueError('truncated width larger than input width')
        elif width == self.width:
            return self
        else:
            return self._truncate_unchecked(width)

    def resize(self, width):
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        elif width < self.width:
            return self.truncate(width)
        else:
            return self.extend(width)

    def _extend_unchecked(self, width):
        self._access_read()
        return Value._auto(Bits(width), expr.ZeroExt(width, self))

    def _truncate_unchecked(self, width):
        return self._auto_lvalue(Bits(width), expr.ConstSlice(0, width, self))

    def repeat(self, count):
        if not isinstance(count, int):
            raise TypeError('repetition count must be an integer')
        elif count < 0:
            raise ValueError('repitition count must not be negative')
        else:
            self._access_read()
            return Value._auto(
                Bits(self.width * count), expr.Repeat(count, self))

    def __getitem__(self, index):
        from .bool import Bool

        slice_type, params = check_slice(self.width, index)

        if slice_type == 'all':
            return super().__getitem__(index)
        elif slice_type == 'const_index':
            index = params
            return self._auto_lvalue(Bool, expr.ConstIndex(index, self))
        elif slice_type == 'dynamic_index':
            index = params
            index._access_read()
            return self._auto_lvalue(Bool, expr.DynamicIndex(index, self))
        elif slice_type == 'const_slice':
            start, length = params
            return self._auto_lvalue(
                Bits(length), expr.ConstSlice(start, length, self))
        else:
            raise TypeError('unsupported index type')

BitsLike.signal_mixin = BitsLikeMixin


class Bits(BitsLike):
    pass


class BitsMixin(BitsLikeMixin):
    def as_uint(self):
        from .int import UInt
        return self._auto_lvalue(UInt(self.width), expr.Nop(self))

    def as_sint(self):
        from .int import SInt
        return self._auto_lvalue(SInt(self.width), expr.Nop(self))

Bits.signal_mixin = BitsMixin
