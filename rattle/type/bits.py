from .type import *
from .. import expr
from ..signal import Value


class Bits(SignalType):
    def __init__(self, width):
        super().__init__()
        self.__width = width

    @property
    def width(self):
        return self.__width

    def __repr__(self):
        return "Bits(%r)" % self.width

    @classmethod
    def concat(cls, *signals):
        # TODO Document lsb first order
        # TODO Check for / coerce into Bits type
        return Value._auto_concat_lvalue(
            signals, cls(sum(signal.width for signal in signals)),
            expr.Concat(signals))


class BitsMixin(SignalMixin):
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

Bits.signal_mixin = BitsMixin
