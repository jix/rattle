from .bitmath import bitindex, bitmask, bitrepeat


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
                return 'u'
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
                return Undef
            else:
                return bool(bitindex(self.value, index))
        elif isinstance(index, slice):
            start = index.start
            stop = index.stop
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

    def __invert__(self):
        return BitVec(self.width, ~self.value, self.mask)

    def __or__(self, other):
        value = self.value | other.value
        mask = (self.mask | other.mask) & ~value
        return BitVec(max(self.width, other.width), value, mask)

    def __and__(self, other):
        return ~(~self | ~other)

    def __xor__(self, other):
        return BitVec(
            max(self.width, other.width),
            self.value ^ other.value,
            self.mask | other.mask)

    def __eq__(self, other):
        if isinstance(other, int):
            return self == bv(other)
        elif not isinstance(other, BitVec):
            return NotImplemented
        diff = self ^ other
        if diff.value != 0:
            return False
        elif diff.mask != 0:
            return Undef
        else:
            return True

    def __ne__(self, other):
        return unot(self == other)

    @staticmethod
    def concat(*values):
        return bv(''.join(str(value) for value in reversed(values)))

    def repeat(self, count):
        return BitVec(
            self.width * count,
            bitrepeat(count, self.width, self.value),
            bitrepeat(count, self.width, self.mask))


class UndefClass:
    def __hash__(self):
        raise TypeError('Undef is unhashable')

    def __eq__(self, other):
        return Undef

    def __repr__(self):
        return 'Undef'

    def __bool__(self):
        # TODO Specific error class
        raise RuntimeError('cannot convert Undef value to bool')

    # TODO Bit operations


Undef = UndefClass()


def bv(value):
    if value is True:
        return BitVec(1, 1)
    elif value is False:
        return BitVec(1, 0)
    elif value is Undef:
        return BitVec(1, 0, 1)
    elif isinstance(value, int):
        return BitVec(value.bit_length(), value)

    # TODO Hex
    if not isinstance(value, str):
        raise TypeError('bv value must be a str')
    if any(c not in '01uU' for c in value):
        raise ValueError('invalid bit value')
    value = value[::-1]
    width = len(value)
    bits = sum((value[i] == '1') << i for i in range(width))
    mask = sum((value[i] in 'uU') << i for i in range(width))

    return BitVec(width, bits, mask)


def ubool(value):
    if value is None:
        return False
    elif isinstance(value, UndefClass):
        return Undef
    elif isinstance(value, (int, bool)):
        return bool(value)
    elif isinstance(value, BitVec):
        return value != 0
    else:
        # TODO Figure out how to extend this
        # TODO Better error message
        raise RuntimeError('value cannot be converted to ubool')


def unot(value):
    false = False
    return ubool(value) == false
