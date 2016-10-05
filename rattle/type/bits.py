from .type import *
from .. import expr
from ..signal import Value, Const
from ..error import ConversionNotImplemented
from ..bitvec import BitVec, bv


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
        if isinstance(value, (int, BitVec)):
            return self.__class__[value].extend(self.width)
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

    def _binary_bitop(self, other, op, const_op):
        generic_type = type(self.signal_type)
        try:
            other = self.signal_type.convert(other, implicit=True)
        except ConversionNotImplemented:
            try:
                other = generic_type.generic_convert(other, implicit=True)
            except ConversionNotImplemented:
                return NotImplemented
        width = max(self.width, other.width)
        a = self.extend(width)
        b = other.extend(width)
        a._access_read()
        b._access_read()
        if isinstance(a, Const) and isinstance(b, Const):
            return generic_type(width)[const_op(a.value, b.value)]
        else:
            return Value._auto(generic_type(width), op(a, b))

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

    def extend(self, width):
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        if width < self.width:
            raise ValueError('extended width less than input width')
        elif width == self.width:
            return self
        else:
            return self._extend_unchecked(width)

    def _extend_unchecked(self, width):
        self._access_read()
        return Value._auto(Bits(width), expr.ZeroExt(width, self))

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
        # TODO Move indexing logic into helper function
        if index == slice(None, None, None):
            return super().__getitem__(index)
        elif isinstance(index, int):
            if index < 0:
                index += self.width
            if index < 0 or index >= self.width:
                raise IndexError('index out of bounds')

            return self._auto_lvalue(Bool, expr.ConstIndex(index, self))
        elif isinstance(index, slice) and index.step is None:
            start = index.start
            stop = index.stop

            if start is None:
                start = 0

            if stop is None:
                stop = self.width

            if isinstance(start, int):
                if start < 0:
                    start += self.width
                if start < 0 or start >= self.width:
                    raise IndexError('start index out of bounds')

                if (isinstance(stop, list) and len(stop) == 1 and
                        isinstance(stop[0], int)):
                    stop = start + stop[0]

                if isinstance(stop, int):
                    if stop < 0:
                        stop += self.width
                    if stop < 0 or stop > self.width:
                        raise IndexError('stop index out of bounds')

                    length = stop - start

                    return self._auto_lvalue(
                        Bits(length), expr.ConstSlice(start, length, self))

        # TODO Non-const indexing
        raise TypeError('Unsupported index type for BitsLike')

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
