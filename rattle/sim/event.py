import abc
from ..type import Clock


class SimEvent(metaclass=abc.ABCMeta):
    def split_event(self):
        yield self


class SimBasicEvent(SimEvent, metaclass=abc.ABCMeta):
    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._tuple() == other._tuple()

    def __hash__(self):
        return hash((type(self), self._tuple()))

    @abc.abstractmethod
    def _tuple(self):
        pass


class SettledEvent(SimBasicEvent):
    def _tuple(self):
        return ()


class TimeEvent(SimBasicEvent):
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def _tuple(self):
        return (self.timestamp,)


class PrimWatchEvent(SimBasicEvent, metaclass=abc.ABCMeta):
    def __init__(self, prim):
        self.prim = prim

    def _tuple(self):
        return (self.prim,)


class PrimChangeEvent(PrimWatchEvent):
    pass


class PrimEdgeEvent(PrimWatchEvent):
    def __init__(self, prim, en=None):
        super().__init__(prim)
        assert prim.shape == (1,)
        assert en is None or en.shape == (1,)
        self.en = en

    def _tuple(self):
        return (self.prim, self.en)


class ChangeEvent(SimBasicEvent):
    def __init__(self, signal):
        self.signal = signal

    def _tuple(self):
        return (self.signal,)

    def split_event(self):
        for prim in self.signal._prims.values():
            yield PrimChangeEvent(prim.simplify_read())


class ClockEvent(SimBasicEvent):
    def __init__(self, signal):
        # TODO use exceptions instead of asserts here
        assert isinstance(signal.signal_type, Clock)
        self.signal = signal

    def _tuple(self):
        return (self.signal,)

    def split_event(self):
        if self.signal.signal_type.gated:
            yield PrimEdgeEvent(
                self.signal.clk._prim().simplify_read(),
                self.signal.en._prim().simplify_read())
        else:
            yield PrimEdgeEvent(self.signal.clk._prim().simplify_read())


__all__ = [
    'SimEvent',
    'SimBasicEvent',
    'SettledEvent',
    'TimeEvent',
    'PrimWatchEvent',
    'PrimChangeEvent',
    'PrimEdgeEvent',
    'ChangeEvent',
    'ClockEvent',
]
