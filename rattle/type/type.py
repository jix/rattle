import abc

from ..signal import Signal
from ..error import ConversionNotImplemented


class SignalMeta(abc.ABCMeta):
    def __getitem__(cls, key):
        return cls.generic_convert(key)


class SignalType(metaclass=SignalMeta):
    def __getitem__(self, key):
        return self.convert(key)

    @property
    def signal_mixin(self):
        return SignalMixin

    @property
    def const_mixin(self):
        return self.signal_mixin

    @abc.abstractproperty
    def _signature_tuple(self):
        pass

    def __eq__(self, other):
        return self is other or self._signature_tuple == other._signature_tuple

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self._signature_tuple)

    def convert(self, signal_or_const):
        if isinstance(signal_or_const, Signal):
            # TODO Skip conversion if already correct signal type
            signal = signal_or_const
            result = signal._convert(self)
            if result is NotImplemented:
                result = self._convert(signal)
            if result is NotImplemented:
                raise ConversionNotImplemented(
                    "conversion from %r to %r not supported" %
                    (signal.signal_type, self))
            return result
        else:
            const = signal_or_const
            try:
                const_signal_fn = const._const_signal
            except AttributeError:
                result = NotImplemented
            else:
                result = const_signal_fn(self)
            if result is NotImplemented:
                result = self._const_signal(const)
            if result is NotImplemented:
                raise ConversionNotImplemented(
                    "conversion from %s to %r not supported" %
                    (type(const).__name__, self))
            return result

    @classmethod
    def generic_convert(cls, signal_or_const):
        if isinstance(signal_or_const, Signal):
            # TODO Skip conversion if already correct signal type
            signal = signal_or_const
            result = signal._generic_convert(cls)
            if result is NotImplemented:
                result = cls._generic_convert(signal)
            if result is NotImplemented:
                raise ConversionNotImplemented(
                    "conversion from %r to %s not supported" %
                    (signal.signal_type, cls.__name__))
            return result
        else:
            const = signal_or_const
            try:
                const_signal_fn = const._generic_const_signal
            except AttributeError:
                result = NotImplemented
            else:
                result = const_signal_fn(cls)
            if result is NotImplemented:
                result = cls._generic_const_signal(const)
            if result is NotImplemented:
                raise ConversionNotImplemented(
                    "conversion from %s to %s not supported" %
                    (type(const).__name__, cls.__name__))
            return result

    def _convert(self, signal):
        # pylint: disable=no-self-use
        return NotImplemented

    @classmethod
    def _generic_convert(cls, signal):
        return NotImplemented

    def _const_signal(self, value):
        # pylint: disable=no-self-use
        return NotImplemented

    @classmethod
    def _generic_const_signal(cls, value):
        return NotImplemented


class SignalMixin(Signal):
    pass
