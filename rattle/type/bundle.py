import collections

from .. import expr
from ..signal import Value, Const
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

    def _const_signal(self, value):
        if isinstance(value, BundleHelper):
            value = value._values

        if isinstance(value, dict):
            expected = set(self.__signals.keys())
            provided = set(value.keys())
            if expected != provided:
                missing = expected - provided
                if missing:
                    raise KeyError(
                        "Expected missing bundle signals " +
                        ', '.join(map(repr, missing)))
                extra = provided - missing
                raise KeyError(
                    "Bundle %r does not contain signals %s" %
                    (self, ', '.join(map(repr, extra))))
            field_signals = {}
            for key, signal_type in self.__signals.items():
                field_signals[key] = signal_type.convert(
                    value[key], implicit=True)
            return Value._auto_concat_lvalue(
                field_signals.values(), self, expr.Bundle(field_signals))
        return NotImplemented

    def _eval_bundle(self, fields):
        if all(isinstance(field, Const) for field in fields.values()):
            values = dict((key, field.value) for key, field in fields.items())
            return Const(self, values)


class BundleMixin(SignalMixin):
    def __getitem__(self, key):
        item_type = self.signal_type.signals[key]
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
