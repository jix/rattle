"""Fixed-width bit-vectors."""
from .type import SignalTypeMeta
from .basic import BasicType, BasicSignal
from ..primitive import *
from ..error import ConversionNotImplemented
from ..bitvec import BitVec, bv
from ..slice import dispatch_getitem
from ..signal import Signal


class BitsLike(BasicType, metaclass=SignalTypeMeta):
    """Abstract superclass for Bits and Int."""
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
        """Bit width."""
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
    """Signal that supports some bit-vector operations.

    In addition to the named methods these signals support:

    * Broadcasted boolean logic using python operators.
    * MSB first concatenation using the ``@`` (``__matmul__``) operator.
    * Indexing and slicing.

    """
    @property
    def width(self):
        """Bit width."""
        return self.signal_type.width

    def __len__(self):
        return self.width

    def concat(self, *others):
        """Concatenate with other signals.

        The concatenation order is LSB first, starting with this signal.
        Use the ``@`` operator for MSB first concatenation.

        The result is always of signal type :class:`Bits`.
        """
        return Bits.concat(self, *others)

    def __matmul__(self, other):
        # TODO Document msb first order for @ operator
        return Bits.concat(other, self)

    def __invert__(self):
        return Bits(self.width)._from_prim(PrimNot(self._prim()))

    def _binary_bitop(self, other, op, result_override=None):
        try:
            other = self.signal_type.convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented

        if result_override is None:
            result_type = self.signal_type
        else:
            result_type = result_override

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
        """Add bits on the MSB side.

        The values of the new bits depend on the concrete signal type.

        Args:
            width (int): the width of the resulting vector.
        """
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        if width < self.width:
            raise ValueError('extended width less than input width')
        elif width == self.width:
            return self
        else:
            return self._extend_unchecked(width)

    def truncate(self, width):
        """Remove bits on the MSB side.

        Args:
            width (int): the width of the resulting vector.
        """
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        if width > self.width:
            raise ValueError('truncated width larger than input width')
        elif width == self.width:
            return self
        else:
            return self._truncate_unchecked(width)

    def resize(self, width):
        """Extend or truncate.

        Extend or truncate, depending on whether width is larger or smaller
        than this signal's width.

        Args:
            width (int): the width of the resulting vector.
        """
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
        """Concatenate multiple copies.

        This concatenates multiple copies of the same signal.
        The result is always of signal type :class:`Bits`.

        Args:
            count (int): number of repetitions.
        """
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
    """Signal type for fixed-width bit-vectors.

    Subclass of :class:`BitsLike`.
    """
    @classmethod
    def concat(cls, *signals):
        """Concatenate bit-vectors.

        The concatenation order is LSB first.
        Use the ``@`` operator for MSB first concatenation.
        """
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
    """Bit-vector signal.

    Most operations are inherited from :class:`BitsLike`.
    This also supports bit-shifts by constant or UInt signal amounts.
    """
    def as_uint(self):
        """Convert into a UInt signal of the same width."""
        from .int import UInt
        return UInt(self.width)._from_prim(self._prim())

    def as_sint(self):
        """Convert into a SInt signal of the same width."""
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
        """Arithmetic right-shift.

        A right shift that shifts in copies of the MSB instead of zeros.
        """
        return self._shift_op(shift, PrimArithShiftRight)
