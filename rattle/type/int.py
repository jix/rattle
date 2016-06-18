import abc

from .type import *
from .bits import *


class Int(Bits, metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def signed(self):
        pass

    @classmethod
    def _generic_const_signal(cls, value):
        if isinstance(value, int):
            if value < 0:
                return SInt[value]
            else:
                return UInt[value]
        else:
            return super()._generic_const_signal(value)


class IntMixin(BitsMixin):
    pass

Int.signal_mixin = IntMixin


class UInt(Int):
    @property
    def signed(self):
        return False

    @classmethod
    def _generic_const_signal(cls, value):
        # pylint: disable=bad-super-call
        # We intentionally skip the Int version as it will call this one
        return super(Int, cls)._generic_const_signal(value)


class SInt(Int):
    def __init__(self, width):
        super().__init__(width)
        if width < 1:
            raise ValueError('the width of a signed integer must be positive')

    @property
    def signed(self):
        return True

    @classmethod
    def _generic_const_signal(cls, value):
        if isinstance(value, int):
            if value < 0:
                width = (~value).bit_length() + 1
            else:
                width = value.bit_length() + 1
            return Const(cls(width), value)
        else:
            return super()._generic_const_signal(value)

# TODO Implement SInt mixin with extend
