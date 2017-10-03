"""Common code for all signal types."""
from functools import reduce
from operator import or_
import abc

from ..signal import Signal
from ..bitvec import BitVec, X, XClass
from ..primitive import PrimConst, PrimTable
from ..error import ConversionNotImplemented, NoCommonSignalType


class SignalTypeMeta(abc.ABCMeta):
    def __getitem__(cls, key):
        return cls.generic_convert(key)


class SignalType(metaclass=SignalTypeMeta):
    """Type of a :class:`rattle.signal.Signal`.

    An instance of this class specifies the set of values that a signal can
    take.

    Signal types can be tested for equality.
    """
    def __getitem__(self, key):
        return self.convert(key)

    @abc.abstractproperty
    def _signature_tuple(self):
        pass

    def __eq__(self, other):
        if not isinstance(other, SignalType):
            return NotImplemented
        return self is other or self._signature_tuple == other._signature_tuple

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self._signature_tuple)

    def convert(self, signal_or_const, *, implicit=False):
        """Convert a signal or constant value to a signal of this type.

        Instead of ``some_type.convert(value)`` you can use the shortcut
        ``some_type[value]``.

        Args:
            signal_or_const: A :class:`rattle.signal.Signal` instance or
                a Python constant.
            implicit (bool): Limit conversions to those that are appropriate
                for an implicit conversion (e.g. when converting arguments).

        Returns:
            A signal of this signal type.

        Raises:
            rattle.error.ConversionNotImplemented: when the given
                argument cannot be converted to this type.
        """
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
        """Convert a signal or constant value to have a type of this class.

        Instead of ``SomeTypeClass.generic_convert(value)`` you can use the
        shortcut ``SomeTypeClass[value]``.

        Args:
            signal_or_const: A :class:`rattle.signal.Signal` instance or
                a Python constant.
            implicit (bool): Limit conversions to those that are appropriate
                for an implicit conversion (e.g. when converting arguments).

        Returns:
            A signal with a signal type that is an instance of this class.

        Raises:
            rattle.error.ConversionNotImplemented: when the given
                argument cannot be converted to have a type of this class.
        """
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
        # pylint: disable=no-self-use, unused-argument
        return NotImplemented

    @classmethod
    def _generic_convert(cls, signal, *, implicit):
        # pylint: disable=unused-argument
        return NotImplemented

    def _const_signal(self, value, *, implicit):
        # pylint: disable=unused-argument
        if isinstance(value, XClass):
            return self._xval()
        else:
            return NotImplemented

    @classmethod
    def _generic_const_signal(cls, value, *, implicit):
        # pylint: disable=unused-argument
        return NotImplemented

    def __or__(self, other):
        if self == other:
            return self
        else:
            return NotImplemented

    @staticmethod
    def common(types):
        """Compute a common type representing values from all given types.

        You can use ``a | b | ...`` instead of
        ``SingalType.common([a, b, ...])``.

        Args:
            types (iterable of SignalTypes): List of types to find a common
                type for.

        Returns:
            A signal type that can represent values of all specified types.

        Raises:
            rattle.error.NoCommonSignalType: when no such type exists or no
                such type can be found.
        """
        # TODO Check that types contains signal types.
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
        """Whether a port of this type will have any reverse connections."""
        return any(flip for (flip, *_shape) in self._prim_shape.values())

    @abc.abstractmethod
    def _unpack(self, unpacker):
        pass

    def unpack(self, signal):
        """Convert a bit-packed signal back into a signal of this type."""
        from ..packing import Unpacker
        packed_type = self[X].packed.signal_type
        signal = packed_type.convert(signal, implicit=True)
        return self._unpack(Unpacker(signal))

    def _initialize_reg_value(self, reg):
        pass
