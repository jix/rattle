from .type import *


class BoolType(SignalType):
    def __repr__(self):
        return "Bool"

Bool = BoolType()
BoolType.__new__ = lambda cls: Bool
