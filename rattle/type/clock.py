from .type import *


# TODO Different clock types for sync/async and with or without initial
class ClockType(SignalType):
    def __repr__(self):
        return "Clock"

    @property
    def _signature_tuple(self):
        return (type(self),)

Clock = ClockType()
ClockType.__new__ = lambda cls: Clock
