def log2up(x):
    if x < 1:
        raise ValueError('log2up requires a positive argument')
    return (x - 1).bit_length()


def log2down(x):
    if x < 1:
        raise ValueError('log2down requires a positive argument')
    return x.bit_length() - 1


def ispow2(x):
    if x < 1:
        return False
    else:
        return not x & (x - 1)


def pow2up(x):
    if x < 1:
        return 1
    else:
        return 1 << log2up(x)


def pow2down(x):
    if x < 1:
        raise ValueError('there is no power of two below 1')
    else:
        return 1 << log2down(x)


def bitmask(high, low=None):
    if low is None:
        return (1 << high) - 1
    else:
        return bitmask(high) ^ bitmask(low)


def signext(bits, value):
    value &= bitmask(bits)
    sign_mask = 1 << (bits - 1)
    return (value ^ sign_mask) - sign_mask


def bitrepeat(count, width, value):
    value &= bitmask(width)
    return sum(value << (width * i) for i in range(count))
