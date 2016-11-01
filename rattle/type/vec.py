from .type import *
from .. import expr
from ..signal import Value, Const
from ..slice import check_slice


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
        slice_type, params = check_slice(len(self), index)

        if slice_type == 'all':
            return super().__getitem__(index)
        elif slice_type == 'const_index':
            index = params
            return self._auto_lvalue(
                self.element_type, expr.ConstIndex(index, self))
        elif slice_type == 'dynamic_index':
            index = params
            index._access_read()
            return self._auto_lvalue(
                self.element_type, expr.DynamicIndex(index, self))
        elif slice_type == 'const_slice':
            start, length = params
            return self._auto_lvalue(
                Vec(length, self.signal_type.element_type),
                expr.ConstSlice(start, length, self))
        else:
            raise TypeError('unsupported index type')

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
