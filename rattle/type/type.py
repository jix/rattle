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

    def convert(self, signal_or_const, *, implicit=False):
        if isinstance(signal_or_const, Signal):
            signal = signal_or_const
            if signal.signal_type == self:
                # This is equality and not subtyping to avoid variance issues
                return signal
            result = signal._convert(self, implicit=implicit)
            if result is NotImplemented:
                result = self._convert(signal, implicit=implicit)
            if result is NotImplemented:
                raise ConversionNotImplemented(
                    "%sconversion from %r to %r not supported" % (
                        "implicit " if implicit else "",
                        signal.signal_type, self))
            return result
        else:
            const = signal_or_const
            try:
                const_signal_fn = const._const_signal
            except AttributeError:
                result = NotImplemented
            else:
                result = const_signal_fn(self, implicit=implicit)
            if result is NotImplemented:
                result = self._const_signal(const, implicit=implicit)
            if result is NotImplemented:
                raise ConversionNotImplemented(
                    "%sconversion from %s to %r not supported" % (
                        "implicit " if implicit else "",
                        type(const).__name__, self))
            return result

    @classmethod
    def generic_convert(cls, signal_or_const, *, implicit=False):
        if isinstance(signal_or_const, Signal):
            signal = signal_or_const
            if signal.signal_type.__class__ == cls:
                # This is equality and not subtyping to avoid variance issues
                return signal
            result = signal._generic_convert(cls, implicit=implicit)
            if result is NotImplemented:
                result = cls._generic_convert(signal, implicit=implicit)
            if result is NotImplemented:
                raise ConversionNotImplemented(
                    "%sconversion from %r to %s not supported" % (
                        "implicit " if implicit else "",
                        signal.signal_type, cls.__name__))
            return result
        else:
            const = signal_or_const
            try:
                const_signal_fn = const._generic_const_signal
            except AttributeError:
                result = NotImplemented
            else:
                result = const_signal_fn(cls, implicit=implicit)
            if result is NotImplemented:
                result = cls._generic_const_signal(const, implicit=implicit)
            if result is NotImplemented:
                raise ConversionNotImplemented(
                    "%sconversion from %s to %s not supported" % (
                        "implicit " if implicit else "",
                        type(const).__name__, cls.__name__))
            return result

    def _convert(self, signal, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        return NotImplemented

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        # pylint: disable=unused-variable
        return NotImplemented

    def _const_signal(self, value, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        return NotImplemented

    @classmethod
    def _generic_const_signal(cls, value, *, implicit):
        # pylint: disable=unused-variable
        return NotImplemented

    def short_repr(self):
        return repr(self)


class SignalMixin(Signal):
    pass
