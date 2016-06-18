from .type import *


class BoolType(SignalType):
    def __repr__(self):
        return "Bool"

    @property
    def _signature_tuple(self):
        return (type(self),)


Bool = BoolType()
BoolType.__new__ = lambda cls: Bool
