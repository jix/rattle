from .type import *
from .. import expr
from ..signal import Value, Const


class Vec(SignalType):
    def __init__(self, length, element_type):
        super().__init__()
        self.__element_type = element_type
        self.__length = length

    @property
    def element_type(self):
        return self.__element_type

    @property
    def length(self):
        return self.__length

    def __repr__(self):
        return "Vec(%i, %r)" % (self.length, self.element_type)

    def short_repr(self):
        return "Vec(%i, %s)" % (self.length, self.element_type.short_repr())

    @property
    def _signature_tuple(self):
        return (type(self), self.length, self.element_type)

    def _const_signal(self, value, *, implicit):
        if isinstance(value, VecHelper):
            value = value._values

        if isinstance(value, (list, tuple)):
            element_signals = [
                self.element_type.convert(el, implicit=implicit)
                for el in value]
            return Value._auto_concat_lvalue(
                element_signals, self, expr.Vec(element_signals))
        return NotImplemented

    def _eval_vec(self, elements):
        if all(isinstance(elemnent, Const) for elemnent in elements):
            return Const(self, tuple(element.value for element in elements))

    @staticmethod
    def _eval_const_index(result_type, index, x):
        if isinstance(x, Const):
            return Const(result_type, x.value[index])

    @staticmethod
    def _eval_const_slice(result_type, start, length, x):
        if isinstance(x, Const):
            return Const(result_type, x.value[start:start + length])


class VecMixin(SignalMixin):
    @property
    def element_type(self):
        return self.signal_type.element_type

    def __getitem__(self, index):
        # TODO Move indexing logic into helper function
        if index == slice(None, None, None):
            return super().__getitem__(index)
        elif isinstance(index, int):
            if index < 0:
                index += len(self)
            if index < 0 or index >= len(self):
                raise IndexError('Vec index out of bounds')

            return self._auto_lvalue(
                self.element_type, expr.ConstIndex(index, self))
        elif isinstance(index, slice) and index.step is None:
            start = index.start
            stop = index.stop

            if start is None:
                start = 0

            if stop is None:
                stop = len(self)

            if isinstance(start, int):
                if start < 0:
                    start += len(self)
                if start < 0 or start >= len(self):
                    raise IndexError('start index out of bounds')

                if (isinstance(stop, list) and len(stop) == 1 and
                        isinstance(stop[0], int)):
                    stop = start + stop[0]

                if isinstance(stop, int):
                    if stop < 0:
                        stop += len(self)
                    if stop < 0 or stop > len(self):
                        raise IndexError('stop index out of bounds')

                    length = stop - start

                    return self._auto_lvalue(
                        Vec(length, self.signal_type.element_type),
                        expr.ConstSlice(start, length, self))

        # TODO Non-const indexing
        raise TypeError('Vec index must be an integer')

    def __len__(self):
        return self.signal_type.length

Vec.signal_mixin = VecMixin


class VecHelper:
    def __init__(self, values):
        self._values = values

    def __repr__(self):
        return 'vec(%s)' % ', '.join(map(repr, self._values))

    # TODO Partial Vec API


def vec(*args):
    if args and all(isinstance(signal, Signal) for signal in args):
        common_type = SignalType.common(signal.signal_type for signal in args)
        return Vec(len(args), common_type)[args]
    return VecHelper(args)
