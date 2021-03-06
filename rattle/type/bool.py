"""Boolean signals."""
from .basic import BasicType, BasicSignal
from ..primitive import *
from ..bitvec import bv, xbool
from ..error import ConversionNotImplemented


class BoolType(BasicType):
    """Boolean signal type.

    Use the existing instance :data:`Bool`.
    """
    def __repr__(self):
        return "Bool"

    @property
    def _signature_tuple(self):
        return (type(self),)

    def _const_signal(self, value, *, implicit):
        # pylint: disable=unused-variable
        try:
            value = xbool(value)
        except TypeError:
            pass
        else:
            return Bool._from_prim(PrimConst(bv(value)))
        return super()._const_signal(value, implicit=implicit)

    @property
    def _prim_width(self):
        return 1

    @property
    def _signal_class(self):
        return BoolSignal

    def _initialize_reg_value(self, reg):
        reg[:] = Bool[False]


Bool = BoolType()
"""Boolean signal type.

Only instance of :class:`BoolType`."""


def _raise(cls):
    # pylint: disable=unused-argument
    raise RuntimeError('use Bool instead of BoolType()')


BoolType.__new__ = _raise


class BoolSignal(BasicSignal):
    """Boolean signal.

    Implements the usual boolean logic operators.
    """
    def __invert__(self):
        return Bool._from_prim(PrimNot(self._prim()))

    def _binary_bitop(self, other, op):
        try:
            other = self.signal_type.convert(other, implicit=True)
        except ConversionNotImplemented:
            return NotImplemented
        return Bool._from_prim(
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

    def repeat(self, count):
        """Repeat a single bit.

        Args:
            count (int): number of repetitions.

        Returns:
            Bits(count): self repeated count times.
        """

        from .bits import Bits
        if not isinstance(count, int):
            raise TypeError('repetition count must be an integer')
        elif count < 0:
            raise ValueError('repitition count must not be negative')
        else:
            return Bits(count)._from_prim(
                PrimRepeat(count, self._prim()))

    @property
    def value(self):
        return self._prim_value()[0]
