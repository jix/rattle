"""Three-valued logic and three-valued bit vectors."""
from .bitmath import bitindex, bitmask, bitrepeat, signext


class BitVec:
    """Three-valued bit vector.

    A fixed width vector, where each item is either True, False or X.
    The string representation is MSB first and uses ``1``, ``0``, and ``x``
    respectively.

    Supported operations using standard Python operators include:

    *   Boolean logic by broadcasting operations and zero-extending on a width
        mismatch
    *   Indexing using int indices, int slices and BitVec indices
    *   Arithmetic (except division, silently truncates overflow)
    *   Arithmetic comparison (unsigned)
    *   Bitshifts
    """
    def __init__(self, width, value, mask=0):
        """Construct a BitVec from the value/mask representation.

        Automatically zeros mask bits in value and truncates value and mask.

        Most of the time you should use the :func:`bv` helper instead for
        constructing BitVec values.
        """
        self.__width = width
        width_mask = bitmask(width)
        self.__value = (value & ~mask) & width_mask
        self.__mask = mask & width_mask

    @property
    def width(self):
        """Bit width."""
        return self.__width

    @property
    def value(self):
        """Value as int using ``0`` in place of ``x``."""
        return self.__value

    @property
    def mask(self):
        """Bit mask that is ``1`` exactly when the the BitVec is ``x``."""
        return self.__mask

    def __str__(self):
        def bit_reprs(bit):
            if bit is False:
                return '0'
            elif bit is True:
                return '1'
            else:
                return 'x'
        return ''.join(bit_reprs(bit) for bit in self)[::-1]

    def __repr__(self):
        return "bv('%s')" % str(self)

    def __iter__(self):
        return (self[i] for i in range(len(self)))

    def __len__(self):
        return self.width

    def __getitem__(self, index):
        if isinstance(index, int):
            if index < 0:
                index += len(self)
            if index < 0 or index >= len(self):
                raise IndexError('BitVec index out of range')
            if bitindex(self.mask, index):
                return X
            else:
                return bool(bitindex(self.value, index))
        elif isinstance(index, BitVec):
            return self._index_bitvec(index)
        elif isinstance(index, slice):
            start = index.start
            stop = index.stop
            if start is None:
                start = 0
            if stop is None:
                stop = self.width
            if index.step is not None:
                # TODO change this
                raise IndexError('BitVec does not support step slices')
            if not isinstance(start, int):
                raise TypeError('BitVec indices must be integers')
            if not isinstance(stop, int):
                raise TypeError('BitVec indices must be integers')
            if start < 0:
                start += len(self)
            if start < 0 or start > len(self):
                raise IndexError('BitVec index out of range')
            if stop < 0:
                stop += len(self)
            if stop < 0 or stop > len(self):
                raise IndexError('BitVec index out of range')

            width = stop - start
            if width < 0:
                raise IndexError('BitVec stop index before start index')

            width_mask = bitmask(width)
            return BitVec(
                width,
                (self.value >> start) & width_mask,
                (self.mask >> start) & width_mask)
        else:
            raise TypeError('BitVec indices must be integers or slices')

    def _index_bitvec(self, index):
        value = self.value
        mask = self.mask | ~bitmask(self.width)

        for i in range(index.width):
            if index[i] is True:
                shift = 1 << i
                value >>= shift
                mask >>= shift
            elif index[i] is X:
                shift = 1 << i
                mask |= (mask >> shift) | ((value >> shift) ^ value)

        if mask & 1:
            return X
        else:
            return bool(value & 1)

    def __invert__(self):
        return BitVec(self.width, ~self.value, self.mask)

    def __or__(self, other):
        if not isinstance(other, BitVec):
            return NotImplemented
        value = self.value | other.value
        mask = (self.mask | other.mask) & ~value
        return BitVec(max(self.width, other.width), value, mask)

    def __and__(self, other):
        if not isinstance(other, BitVec):
            return NotImplemented
        return ~(~self | ~other)

    def __xor__(self, other):
        if not isinstance(other, BitVec):
            return NotImplemented
        return BitVec(
            max(self.width, other.width),
            self.value ^ other.value,
            self.mask | other.mask)

    def __add__(self, other):
        if not isinstance(other, BitVec):
            return NotImplemented
        low = self.value + other.value
        high = low + self.mask + other.mask
        mask = (low ^ high) | self.mask | other.mask
        return BitVec(max(self.width, other.width), low, mask)

    def __sub__(self, other):
        if not isinstance(other, BitVec):
            return NotImplemented
        diff = self.value - other.value
        low = diff - other.mask
        high = diff + self.mask
        mask = (low ^ high) | self.mask | other.mask
        return BitVec(max(self.width, other.width), low, mask)

    def __mul__(self, other):
        width = max(self.width, other.width)
        if self.mask or other.mask:
            # TODO Is there an efficient better approximation?
            return BitVec(width, 0, -1)
        return BitVec(width, self.value * other.value)

    def __eq__(self, other):
        """Three-valued equality.

        Use :meth:`same_as` to test for equivalence including don't know
        positions.
        """
        if isinstance(other, int):
            return self == bv(other)
        elif not isinstance(other, BitVec):
            return NotImplemented
        diff = self ^ other
        if diff.value != 0:
            return False
        elif diff.mask != 0:
            return X
        else:
            return True

    def __ne__(self, other):
        return xnot(self == other)

    def __lt__(self, other):
        if not isinstance(other, BitVec):
            return NotImplemented
        width = max(self.width, other.width)
        a = BitVec(width + 1, self.value, self.mask)
        b = BitVec(width + 1, other.value, other.mask)

        return (a - b)[-1]

    def __le__(self, other):
        return xnot(self > other)

    def __gt__(self, other):
        if not isinstance(other, BitVec):
            return NotImplemented
        return other < self

    def __ge__(self, other):
        return xnot(self < other)

    def sign_wrap(self):
        """Negate MSB.

        Unsigned comparison of values with negated signs results in a signed
        comparison.
        """
        if self.width == 0:
            return BitVec(0, 0)
        else:
            return BitVec(
                self.width, self.value ^ (1 << (self.width - 1)), self.mask)

    @staticmethod
    def concat(*values):
        """Concatenate multiple bit vectors.

        The first given vector comes first (LSB) in the resulting vector.
        """
        # TODO Add __matmul__ for concatenation?
        # TODO Use more efficient implementation?
        return bv(''.join(str(value) for value in reversed(values)))

    def repeat(self, count):
        """Concatenate multiple copies of the same bit vector."""
        # TODO Type/value checking
        return BitVec(
            self.width * count,
            bitrepeat(count, self.width, self.value),
            bitrepeat(count, self.width, self.mask))

    def values(self):
        """Generate all possible values for don't know bits.

        Returns a generator over all values that could be equal to self (i.e.
        all ``x`` so that ``(x == self) is not False``).
        """
        i = bitmask(self.width)
        while i >= 0:
            i &= self.mask
            yield i | self.value
            i -= 1

    def combine(self, other):
        """Nondeterministic choice between self and other.

        Returns a vector that has the same bits where self and other agree and
        don't knows otherwise.
        """
        if other is None:
            return self
        return BitVec(
            max(self.width, other.width),
            self.value,
            (self.value ^ other.value) | self.mask | other.mask)

    def extend(self, width):
        """Zero-extend a vector."""
        # TODO Type/value checking
        return BitVec(width, self.value, self.mask)

    def sign_extend(self, width):
        """Sign-extend a vector."""
        return BitVec(
            width,
            signext(self.width, self.value),
            signext(self.width, self.mask))

    def same_as(self, other):
        """Equivalence including don't know positions."""
        return (
            self.width == other.width and
            self.value == other.value and
            self.mask == other.mask)

    def updated_at(self, pos, other):
        """Replace bits inside a vector.

        Returns a new vector where the bits starting at ``pos`` are replaced by
        the bits from the vector ``other``.
        """
        update_mask = bitmask(pos + other.width, pos)
        return BitVec(
            self.width,
            (self.value & ~update_mask) | (other.value << pos),
            (self.mask & ~update_mask) | (other.mask << pos))

    def __lshift__(self, shift):
        return BitVec(self.width, self.value << shift, self.mask << shift)

    def __rshift__(self, shift):
        return BitVec(self.width, self.value >> shift, self.mask >> shift)

    def arith_rshift(self, shift):
        """Arithmetic right shift."""
        return BitVec(
            self.width,
            signext(self.width, self.value) >> shift,
            signext(self.width, self.mask) >> shift)


class XClass:
    """The don't know value.

    Supports boolean logic and converts to constant signals of any signal type.

    Use the existing instance :data:`X`.
    """
    def __hash__(self):
        raise TypeError('X is unhashable')

    def __eq__(self, other):
        """Implements boolean logic, i.e. always returns X.

        Use ``some_value is X`` to test for don't know values.
        """
        return X

    def __repr__(self):
        return 'X'

    def __bool__(self):
        """Conversion to ``bool`` raises an exception.

        Use :func:`xbool` to convert to three-valued logic.
        """
        # TODO Specific error class
        raise RuntimeError('cannot convert X value to bool')

    def __and__(self, other):
        if other is True or isinstance(other, XClass):
            return X
        elif other is False:
            return False
        else:
            return NotImplemented

    def __rand__(self, other):
        return self & other

    def __or__(self, other):
        if other is False or isinstance(other, XClass):
            return X
        elif other is True:
            return True
        else:
            return NotImplemented

    def __ror__(self, other):
        return self & other

    def __xor__(self, other):
        if isinstance(other, (bool, XClass)):
            return X
        else:
            return NotImplemented

    def __rxor__(self, other):
        return self ^ other


X = XClass()
"""Only instance of the :class:`XClass` type."""


def _raise(cls):  # pylint: disable=unused-argument
    raise RuntimeError('use X instead of XClass()')


XClass.__new__ = _raise


def bv(value):
    """Construct a BitVec.

    This helper function supports the following inputs:

    *   A string representation of a bit vector (``0``, ``1`` and ``x`` MSB
        first).
    *   An int ``x``, resulting in a bit vector of width ``x.bit_length()``.
    """
    if value is True:
        return BitVec(1, 1)
    elif value is False:
        return BitVec(1, 0)
    elif value is X:
        return BitVec(1, 0, 1)
    elif isinstance(value, int):
        return BitVec(value.bit_length(), value)
    # TODO Make it possible to extend this

    # TODO Hex
    if not isinstance(value, str):
        # TODO incorrect error message
        raise TypeError('bv value must be a str')
    if any(c not in '01xX' for c in value):
        raise ValueError('invalid bit value')
    value = value[::-1]
    width = len(value)
    bits = sum((value[i] == '1') << i for i in range(width))
    mask = sum((value[i] in 'xX') << i for i in range(width))

    return BitVec(width, bits, mask)


def xbool(value):
    """Convert to three-valued logic."""
    if value is None:
        return False
    elif isinstance(value, XClass):
        return X
    elif isinstance(value, (int, bool)):
        return bool(value)
    elif isinstance(value, BitVec):
        return value != 0
    else:
        # TODO Figure out how to extend this
        raise TypeError('value cannot be converted to xbool')


def xnot(value):
    """Convert to three-valued logic and negate."""
    false = False
    return xbool(value) == false


__all__ = [
    'BitVec',
    'XClass',
    'X',
    'bv',
    'xbool',
    'xnot',
]
