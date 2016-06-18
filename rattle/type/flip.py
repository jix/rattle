from .type import *
from ..signal import *


class Flip(SignalType):
    def __new__(cls, signal_type):
        if isinstance(signal_type, Flip):
            return signal_type.unflipped
        else:
            return super().__new__(cls)

    def __init__(self, signal_type):
        super().__init__()
        self.__unflipped = signal_type

    @property
    def unflipped(self):
        return self.__unflipped

    def __repr__(self):
        return "Flip(%r)" % self.unflipped

    @property
    def _signature_tuple(self):
        return (type(self), self.unflipped)


class FlipMixin(SignalMixin):
    # TODO Implement flipping of assignments

    def _deflip(self):
        return self.flip()

Flip.signal_mixin = FlipMixin
