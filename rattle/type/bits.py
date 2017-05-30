from .type import SignalTypeMeta
from .basic import BasicType, BasicSignal
from ..primitive import *
from ..error import ConversionNotImplemented
from ..bitvec import BitVec, bv
from ..slice import dispatch_getitem
from ..signal import Signal


class BitsLike(BasicType, metaclass=SignalTypeMeta):
    # pylint: disable=abstract-method
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
    def _generic_const_signal(cls, value, *, implicit):
        from .bool import Bool
        if isinstance(value, int):
            if value < 0:
                raise ValueError(
                    "cannot convert negative value to %s" % cls.__name__)
            width = value.bit_length()
            value = BitVec(width, value)
        elif isinstance(value, str):
            value = bv(value)

        if isinstance(value, BitVec):
            return Bits(value.width)._from_prim(PrimConst(value))
        elif isinstance(value, (tuple, list)) and not implicit:
            value = [Bool[x] for x in value]
            return Bits(len(value))._from_prim(
                PrimConcat([x._prim() for x in value]))
        else:
            return super()._generic_const_signal(value, implicit=implicit)

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        from .vec import Vec
        from .bool import Bool
        if Signal.isinstance(signal, Vec) and signal.element_type == Bool:
            return cls[list(signal)]
        return super()._generic_convert(signal, implicit=implicit)

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
            return Bits(self.width)._from_prim(PrimConst(value))
        elif isinstance(value, (tuple, list)) and not implicit:
            if len(value) != self.width:
                raise ValueError(
                    "wrong length (%i) for %r" % (len(value), self))
            return Bits[value]
        else:
            return super()._const_signal(value, implicit=implicit)

    def _convert(self, signal, *, implicit):
        from .vec import Vec
        from .bool import Bool
        if Signal.isinstance(signal, Vec) and signal.element_type == Bool:
            return self[list(signal)]
        return super()._convert(signal, implicit=implicit)

    @property
    def _prim_width(self):
        return self.width

    def _initialize_reg_value(self, reg):
        reg[:] = BitVec(self.width, 0)


class BitsLikeSignal(BasicSignal):
    @property
    def width(self):
        return self.signal_type.width

    def __len__(self):
        return self.width

    def concat(self, *others):
        return Bits.concat(self, *others)

    def __matmul__(self, other):
        # TODO Document msb first order for @ operator
        return Bits.concat(other, self)

    def __invert__(self):
        return Bits(self.width)._from_prim(PrimNot(self._prim()))

    def _binary_bitop(self, other, op, result_type=None):
        try:
            other = self.signal_type.convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented

        if result_type is None:
            result_type = self.signal_type

        return result_type._from_prim(
            op(self._prim(), other._prim()))

    def __and__(self, other):
        return self._binary_bitop(other, PrimAnd)

    def __rand__(self, other):
        return self.__and__(other)

    def __or__(self, other):
        return self._binary_bitop(other, PrimOr)

    def __ror__(self, other):
        return self.__or__(other)

    def __xor__(self, other):
        return self._binary_bitop(other, PrimXor)

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
        return Bits(width)._from_prim(
            PrimZeroExt(width, self._prim()))

    def _truncate_unchecked(self, width):
        return Bits(width)._from_prim(
            PrimSlice(0, width, self._prim()))

    def repeat(self, count):
        if not isinstance(count, int):
            raise TypeError('repetition count must be an integer')
        elif count < 0:
            raise ValueError('repitition count must not be negative')
        else:
            return Bits(count * self.width)._from_prim(
                PrimRepeat(count, self._prim()))

    __getitem__ = dispatch_getitem

    def _getitem_all(self):
        return self

    def _getitem_const_index(self, index):
        from .bool import Bool
        return Bool._from_prim(PrimSlice(index, 1, self._prim()))

    def _getitem_dynamic_index(self, index):
        from .bool import Bool
        return Bool._from_prim(
            PrimBitIndex(index._prim(), self._prim()))

    def _getitem_const_slice(self, start, length):
        return Bits(length)._from_prim(
            PrimSlice(start, length, self._prim()))

    def _getitem_unknown(self, index):
        res = [self[i] for i in range(self.width)][index]
        if isinstance(res, list):
            return Bits(len(res))[res]
        else:
            return res

    @property
    def value(self):
        return self._prim_value()


class Bits(BitsLike):
    @classmethod
    def concat(cls, *signals):
        # TODO Document lsb first order
        # TODO Allow concat lvalue?
        signals = [
            Bits.generic_convert(signal, implicit=True) for signal in signals]
        width = sum(signal.width for signal in signals)
        return Bits(width)._from_prim(
            PrimConcat(signal._prim() for signal in signals))

    @property
    def _signal_class(self):
        return BitsSignal

    @classmethod
    def _prim(cls, prim):
        return Bits(prim.width)._from_prim(prim)


class BitsSignal(BitsLikeSignal):
    def as_uint(self):
        from .int import UInt
        return UInt(self.width)._from_prim(self._prim())

    def as_sint(self):
        from .int import SInt
        return SInt(self.width)._from_prim(self._prim())

    def _shift_op(self, shift, op):
        from .int import UInt
        try:
            shift = UInt.generic_convert(shift, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        return self.signal_type._from_prim(op(self._prim(), shift._prim()))

    def __lshift__(self, shift):
        return self._shift_op(shift, PrimShiftLeft)

    def __rshift__(self, shift):
        return self._shift_op(shift, PrimShiftRight)

    def arith_rshift(self, shift):
        return self._shift_op(shift, PrimArithShiftRight)
