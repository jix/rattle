import abc

from .type import *
from .bits import *


class Int(Bits, metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def signed(self):
        pass


class IntMixin(BitsMixin):
    pass

Int.signal_mixin = IntMixin


class UInt(Int):
    @property
    def signed(self):
        return False


class SInt(Int):
    def __init__(self, width):
        super().__init__(width)
        if width < 1:
            raise ValueError('the width of a signed integer must be positive')

    @property
    def signed(self):
        return True
