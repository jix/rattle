from .type import *


class Bits(SignalType):
    def __init__(self, width):
        super().__init__()
        self.__width = width

    @property
    def width(self):
        return self.__width

    def __repr__(self):
        return "Bits(%r)" % self.width


class BitsMixin(SignalMixin):
    pass

Bits.signal_mixin = BitsMixin
