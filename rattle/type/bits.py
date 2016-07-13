from .type import *
from .. import expr
from ..signal import Value, Const
from ..error import ConversionNotImplemented
from ..bitmath import signext


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
    def _generic_const_signal(cls, value):
        if isinstance(value, int):
            if value < 0:
                raise ValueError(
                    "cannot convert negative value to %s" % cls.__name__)
            width = value.bit_length()
            return Const(cls(width), value)
        else:
            return super()._generic_const_signal(value)

    def _const_signal(self, value):
        if isinstance(value, int):
            return self.__class__[value].extend(self.width)
        else:
            return super()._const_signal(value)


class BitsLikeMixin(SignalMixin):
    @property
    def width(self):
        return self.signal_type.width

    def concat(self, *others):
        return Bits.concat(self, *others)

    def __matmul__(self, other):
        # TODO Document msb first order for @ operator
        return Bits.concat(other, self)

    def extend(self, width):
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        if width < self.width:
            raise ValueError('extended width less than input width')
        elif width == self.width:
            return self
        else:
            return Bits(width - self.width)[0] @ self

BitsLike.signal_mixin = BitsLikeMixin


class BitsLikeConstMixin(Const, BitsLikeMixin):
    def extend(self, width):
        if not isinstance(width, int):
            raise TypeError('signal width must be an integer')
        if width < self.width:
            raise ValueError('extended width less than input width')
        elif width == self.width:
            return self
        else:
            return Const(Bits(width), self.value)

BitsLike.const_mixin = BitsLikeConstMixin


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


class BitsConstMixin(BitsLikeConstMixin, BitsMixin):
    def as_uint(self):
        from .int import UInt
        return UInt(self.width)[self.value]

    def as_sint(self):
        from .int import SInt
        return SInt(self.width)[signext(self.width, self.value)]

Bits.const_mixin = BitsConstMixin
