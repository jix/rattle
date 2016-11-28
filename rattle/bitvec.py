from .bitmath import bitindex, bitmask, bitrepeat, signext


class BitVec:
    def __init__(self, width, value, mask=0):
        self.__width = width
        width_mask = bitmask(width)
        self.__value = (value & ~mask) & width_mask
        self.__mask = mask & width_mask

    @property
    def width(self):
        return self.__width

    @property
    def value(self):
        return self.__value

    @property
    def mask(self):
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
            if start < 0 or start >= len(self):
                raise IndexError('BitVec index out of range')
            if stop < 0:
                stop += len(self)
            if stop < 0 or stop > len(self):
                raise IndexError('BitVec index out of range')

            width = stop - start
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
        if self.width == 0:
            return BitVec(0, 0)
        else:
            return BitVec(
                self.width, self.value ^ (1 << (self.width - 1)), self.mask)

    @staticmethod
    def concat(*values):
        return bv(''.join(str(value) for value in reversed(values)))

    def repeat(self, count):
        # TODO Type/value checking
        return BitVec(
            self.width * count,
            bitrepeat(count, self.width, self.value),
            bitrepeat(count, self.width, self.mask))

    def values(self):
        i = bitmask(self.width)
        while i >= 0:
            i &= self.mask
            yield i | self.value
            i -= 1

    def combine(self, other):
        return BitVec(
            max(self.width, other.width),
            self.value,
            (self.value ^ other.value) | self.mask | other.mask)

    def extend(self, width):
        # TODO Type/value checking
        return BitVec(width, self.value, self.mask)

    def sign_extend(self, width):
        return BitVec(
            width,
            signext(self.width, self.value),
            signext(self.width, self.mask))


class XClass:
    def __hash__(self):
        raise TypeError('X is unhashable')

    def __eq__(self, other):
        return X

    def __repr__(self):
        return 'X'

    def __bool__(self):
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


def _raise(cls):
    raise RuntimeError('use X instead of XClass()')

XClass.__new__ = _raise


def bv(value):
    if value is True:
        return BitVec(1, 1)
    elif value is False:
        return BitVec(1, 0)
    elif value is X:
        return BitVec(1, 0, 1)
    elif isinstance(value, int):
        return BitVec(value.bit_length(), value)

    # TODO Hex
    if not isinstance(value, str):
        raise TypeError('bv value must be a str')
    if any(c not in '01xX' for c in value):
        raise ValueError('invalid bit value')
    value = value[::-1]
    width = len(value)
    bits = sum((value[i] == '1') << i for i in range(width))
    mask = sum((value[i] in 'xX') << i for i in range(width))

    return BitVec(width, bits, mask)


def xbool(value):
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
        # TODO Better error message
        raise RuntimeError('value cannot be converted to xbool')


def xnot(value):
    false = False
    return xbool(value) == false
