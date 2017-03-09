import abc


class SimEvent(metaclass=abc.ABCMeta):
    pass


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


class WatchEvent(SimBasicEvent, metaclass=abc.ABCMeta):
    def __init__(self, prim):
        self.prim = prim

    def _tuple(self):
        return (self.prim,)


class ChangeEvent(WatchEvent):
    pass


class EdgeEvent(WatchEvent):
    def __init__(self, prim, old, new):
        super().__init__(prim)
        self.old, self.new = old, new

    def _tuple(self):
        return (self.prim, self.old, self.new)
