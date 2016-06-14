from .type import *


# TODO Different clock types for sync/async and with or without initial
class ClockType(SignalType):
    def __repr__(self):
        return "Clock"

Clock = ClockType()
ClockType.__new__ = lambda cls: Clock
