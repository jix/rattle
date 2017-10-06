"""Fixed length homogeneous vectors."""
from .type import SignalType
from ..signal import Signal
from ..primitive import *
from ..slice import dispatch_getitem
from ..bitmath import log2up
from ..bitvec import BitVec
from ..error import InvalidSignalAssignment


class Vec(SignalType):
    """Fixed length homogeneous vector signal type."""
    def __init__(self, length, element_type):
        """Create a vector signal type.

        Args:
            length (int): The number of elements in the vector.
            element_type (SignalType): The signal type of the indivdual
                elements.
        """

        super().__init__()
        self.__element_type = element_type
        self.__length = length

    @property
    def element_type(self):
        """Signal type of the indivdual elements."""
        return self.__element_type

    @property
    def length(self):
        """Number of elements."""
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
            # TODO Check length
            transposed = {k: [] for k in self._prim_shape}

            for element in value:
                element = self.element_type.convert(element, implicit=implicit)
                for field, prim in element._prims.items():
                    transposed[field].append(prim)

            return self._from_prims({
                k: PrimTable(v) for k, v in transposed.items()})
        return super()._const_signal(value, implicit=implicit)

    @property
    def _signal_class(self):
        return VecSignal

    @property
    def _prim_shape(self):
        return {
            k: v + (self.length,)
            for k, v in self.element_type._prim_shape.items()}

    def _unpack(self, unpacker):
        signals = []
        for _ in range(self.length):
            signals.append(
                self.element_type._unpack(unpacker))
        return self[signals]

    def _initialize_reg_value(self, reg):
        try:
            for i in range(self.length):
                self.element_type._initialize_reg_value(reg[i])
        except InvalidSignalAssignment:
            pass


class VecSignal(Signal):
    """Fixed length homogeneous vector signal.

    Supports indexing and slicing using constants and indexing using signals.
    """
    @property
    def element_type(self):
        """Signal type of the indivdual elements."""
        return self.signal_type.element_type

    def __len__(self):
        return self.signal_type.length

    __getitem__ = dispatch_getitem

    def _getitem_all(self):
        return self

    def _getitem_const_index(self, index):
        return self._getitem_prim(index)

    def _getitem_dynamic_index(self, index):
        return self._getitem_prim(index._prim())

    def _getitem_prim(self, index_prim):
        return self.element_type._from_prims({
            k: PrimIndex(index_prim, v)
            for k, v in self._prims.items()})

    def _getitem_const_slice(self, start, length):
        return Vec(length, self.element_type)[
            [self[i] for i in range(start, start + length)]]

    def _getitem_unknown(self, index):
        res = list(self)[index]
        if isinstance(res, list):
            return Vec(len(res), self.element_type)[res]
        else:
            return res

    @property
    def value(self):
        return tuple(self[i].value for i in range(self.signal_type.length))

    def _add_to_trace(self, trace, scope, name):
        for i in range(self.signal_type.length):
            self[i]._add_to_trace(trace, scope + [('struct', name)], str(i))

    def _pack(self, packer):
        for i in range(self.signal_type.length):
            self[i]._pack(packer)


class VecHelper:
    """Helper to construct Vec signals from Python constants.

    This is returned by the :func:`vec` function when some of the arguments are
    Python constants.
    It will implicitly convert to :class:`Vec` signals.
    """
    def __init__(self, values):
        self._values = values

    def __repr__(self):
        return 'vec(%s)' % ', '.join(map(repr, self._values))

    # TODO Partial Vec API


def vec(*args):
    """Construct a Vec signal by listing its elements.

    When not all arguments are signals, this will return a class::`VecHelper`.
    """
    if args and all(isinstance(signal, Signal) for signal in args):
        common_type = SignalType.common(signal.signal_type for signal in args)
        return Vec(len(args), common_type)[args]
    return VecHelper(args)
