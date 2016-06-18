import collections

from .. import expr
from .type import *


class Bundle(SignalType):
    def __init__(self, **kwds):
        super().__init__()
        # TODO Allow different initialization
        self.__signals = collections.OrderedDict(sorted(kwds.items()))

    @property
    def signals(self):
        # TODO Use something like a frozen ordered dict instead of a copy
        return collections.OrderedDict(self.__signals.items())

    def __repr__(self):
        return "Bundle(%s)" % ', '.join(
            "%s=%r" % item for item in self.signals.items())

    @property
    def _signature_tuple(self):
        return (
            type(self),
            tuple((key, signal) for key, signal in self.signals.items()))


class BundleMixin(SignalMixin):
    def __getitem__(self, key):
        if isinstance(key, slice):
            return super().__getitem__(key)
        item_type = self.signal_type.signals[key]
        return self._auto_lvalue(item_type, expr.Field(key, self))._deflip()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError()  # TODO Message

Bundle.signal_mixin = BundleMixin
