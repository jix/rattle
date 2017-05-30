import abc
import collections

from .type import SignalType
from ..signal import Signal
from ..error import InvalidSignalAssignment


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
            prims = {}
            for field, field_type in self.__fields.items():
                field_signal = field_type.convert(
                    value[field], implicit=implicit)
                prims.update(
                    ((field,) + k, v)
                    for k, v in field_signal._prims.items())
            return self._from_prims(prims)
        return super()._const_signal(value, implicit=implicit)

    @property
    def _signal_class(self):
        return BundleSignal

    @property
    def _prim_shape(self):
        shape = {}
        for field, field_type in self.__fields.items():
            shape.update(
                ((field,) + k, v)
                for k, v in field_type._prim_shape.items())
        return shape

    def _unpack(self, unpacker):
        signals = {}
        for key, field_type in self.__fields.items():
            signals[key] = field_type._unpack(unpacker)
        return self[signals]

    def _initialize_reg_value(self, reg):
        for key, field_type in self.__fields.items():
            field = reg._getitem_raw(key)
            try:
                field_type._initialize_reg_value(field)
            except InvalidSignalAssignment:
                pass


class BundleFields(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def _getitem_raw(self, key):
        pass

    @abc.abstractproperty
    def _field_names(self):
        pass

    def __getitem__(self, key):
        return self._getitem_raw(key)._bundle_field_access()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError()  # TODO Message

    def __neg__(self):
        return PartialBundle(self, True, False)

    def __pos__(self):
        return PartialBundle(self, False, True)


class BundleSignal(BundleFields, Signal):
    def _getitem_raw(self, key):
        item_type = self.signal_type.fields[key]
        return item_type._from_prims({
            k[1:]: v
            for k, v in self._prims.items()
            if k[0] == key})

    @property
    def _field_names(self):
        return set(self.signal_type.fields.keys())

    @property
    def value(self):
        return {
            field: self[field].value
            for field in self.signal_type.fields}

    def _add_to_trace(self, trace, scope, name):
        for key in self.signal_type.fields.keys():
            self[key]._add_to_trace(trace, scope + [('struct', name)], key)

    # TODO Better repr

    def _pack(self, packer):
        for key in self.signal_type.fields.keys():
            self._getitem_raw(key)._pack(packer)


class BundleHelper(BundleFields):
    def __init__(self, values):
        self._values = values

    def __repr__(self):
        return 'bundle(%s)' % (
            ', '.join('%s=%r' % item for item in self._values.items()))

    def _getitem_raw(self, key):
        return self._values[key]

    @property
    def _field_names(self):
        return set(self._values.keys())


def bundle(**kwds):
    if all(isinstance(signal, Signal) for signal in kwds.values()):
        signal_types = dict(
            (name, signal.signal_type) for name, signal in kwds.items())
        signal_type = Bundle(**signal_types)
        return signal_type[kwds]
    else:
        return BundleHelper(kwds)


class PartialBundle:
    def __init__(self, value, allow_extra, allow_missing):
        if not isinstance(value, BundleFields):
            raise TypeError('value needs to implement BundleFields')
        self._value = value
        self._allow_extra, self._allow_missing = allow_extra, allow_missing

    def _assign_to_signal(self, signal):
        if not Signal.isinstance(signal, Bundle):
            return False

        lvalue_field_names = signal._field_names
        rvalue_field_names = self._value._field_names

        if not self._allow_missing:
            missing = lvalue_field_names - rvalue_field_names
            if missing:
                raise KeyError(
                    'assigned bundle is missing fields %r' % (tuple(missing),))
        if not self._allow_extra:
            extra = rvalue_field_names - lvalue_field_names
            if extra:
                raise KeyError(
                    'assigned bundle has extra fields %r' % (tuple(extra),))

        for field in sorted(lvalue_field_names & rvalue_field_names):
            signal._getitem_raw(field)[:] = self._value._getitem_raw(field)

        return True
