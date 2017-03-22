from functools import reduce
from operator import or_
import abc

from ..signal import Signal
from ..bitvec import BitVec, XClass
from ..primitive import PrimConst, PrimTable
from ..error import ConversionNotImplemented, NoCommonSignalType


class SignalTypeMeta(abc.ABCMeta):
    def __getitem__(cls, key):
        return cls.generic_convert(key)


class SignalType(metaclass=SignalTypeMeta):
    def __getitem__(self, key):
        return self.convert(key)

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
        if isinstance(value, XClass):
            return self._xval()
        else:
            return NotImplemented

    @classmethod
    def _generic_const_signal(cls, value, *, implicit):
        # pylint: disable=unused-variable
        return NotImplemented

    def __or__(self, other):
        if self == other:
            return self
        else:
            return NotImplemented

    @staticmethod
    def common(types):
        try:
            return reduce(or_, types)
        except TypeError:
            raise NoCommonSignalType(
                "no common signal type for given types %r" % tuple(types))

    @abc.abstractproperty
    def _prim_shape(self):
        pass

    @abc.abstractproperty
    def _signal_class(self):
        pass

    def _from_prims(self, prims):
        return self._signal_class._from_prims(self, prims)

    def _xval(self):
        prims = {}
        for key, (_flip, width, *dimensions) in self._prim_shape.items():
            xval = PrimConst(BitVec(width, 0, -1))
            for size in dimensions:
                xval = PrimTable((xval,) * size)

            prims[key] = xval
        return self._from_prims(prims)

    @property
    def contains_flipped(self):
        return any(flip for (flip, *_shape) in self._prim_shape.values())


class BasicType(SignalType, metaclass=SignalTypeMeta):
    @property
    def _prim_shape(self):
        return {(): (False, self._prim_width,)}

    @abc.abstractproperty
    def _prim_width(self):
        pass

    def _from_prim(self, prim):
        return self._from_prims({(): prim})
