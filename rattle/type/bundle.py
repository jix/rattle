import collections

from .. import expr
from ..signal import Value
from .type import *


class Bundle(SignalType):
    def __init__(self, **kwds):
        super().__init__()
        # TODO Allow different initialization
        self.__fields = collections.OrderedDict(sorted(kwds.items()))

    @property
    def fields(self):
        # TODO Use something like a frozen ordered dict instead of a copy
        return collections.OrderedDict(self.__fields.items())

    def __repr__(self):
        return "Bundle(%s)" % ', '.join(
            "%s=%r" % item for item in self.fields.items())

    def short_repr(self):
        return "Bundle(%s)" % ', '.join(self.fields.keys())

    @property
    def _signature_tuple(self):
        return (
            type(self),
            tuple((key, field) for key, field in self.fields.items()))

    def _const_signal(self, value, *, implicit):
        if isinstance(value, BundleHelper):
            value = value._values

        if isinstance(value, dict):
            expected = set(self.__fields.keys())
            provided = set(value.keys())
            if expected != provided:
                missing = expected - provided
                if missing:
                    raise KeyError(
                        "Expected missing bundle fields " +
                        ', '.join(map(repr, missing)))
                extra = provided - missing
                raise KeyError(
                    "Bundle %r does not contain fields %s" %
                    (self, ', '.join(map(repr, extra))))
            field_signals = {}
            for key, field_type in self.__fields.items():
                field_signals[key] = field_type.convert(
                    value[key], implicit=implicit)
            return Value._auto_concat_lvalue(
                field_signals.values(), self, expr.Bundle(field_signals))
        return NotImplemented


class BundleMixin(SignalMixin):
    def __getitem__(self, key):
        item_type = self.signal_type.fields[key]
        return self._auto_lvalue(item_type, expr.Field(key, self))._deflip()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError()  # TODO Message

    # TODO Better repr

Bundle.signal_mixin = BundleMixin


class BundleHelper:
    def __init__(self, values):
        self._values = values

    def __repr__(self):
        return 'bundle(%s)' % (
            ', '.join('%s=%r' % item for item in self._values.items()))

    # TODO Partial Bundle API


def bundle(**kwds):
    if all(isinstance(signal, Signal) for signal in kwds.values()):
        signal_types = dict(
            (name, signal.signal_type) for name, signal in kwds.items())
        signal_type = Bundle(**signal_types)
        return signal_type[kwds]
    else:
        return BundleHelper(kwds)
