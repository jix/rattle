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


class VecMixin(SignalMixin):
    @property
    def element_type(self):
        return self.signal_type.element_type

    def __getitem__(self, index):
        if index == slice(None, None, None):
            return super().__getitem__(index)
        elif isinstance(index, int):
            if index < 0:
                index += len(self)
            if index < 0 or index >= len(self):
                raise IndexError('Vec index out of bounds')

            return self._auto_lvalue(
                self.element_type, expr.ConstIndex(index, self))
        else:
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
        first_type = args[0].signal_type
        if all(signal.signal_type == first_type for signal in args[1:]):
            return Vec(len(args), first_type)[args]
    else:
        return VecHelper(args)
