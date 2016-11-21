from .signal import Signal


def check_slice(width, index):
    from .type import Bits
    if index == slice(None, None, None):
        return ('all',)
    elif isinstance(index, int):
        if index < 0:
            index += width
        if index < 0 or index >= width:
            raise IndexError('index out of bounds')
        return 'const_index', index
    elif isinstance(index, Signal):
        index_width = (width - 1).bit_length()
        index = Bits(index_width).convert(index, implicit=True)
        return 'dynamic_index', index
    elif isinstance(index, slice) and index.step is None:
        start = index.start
        stop = index.stop
        if start is None:
            start = 0
        if stop is None:
            stop = width

        if isinstance(start, int):
            if start < 0:
                start += width
            if start < 0 or start >= width:
                raise IndexError('start index out of bounds')
            if (isinstance(stop, list) and len(stop) == 1 and
                    isinstance(stop[0], int)):
                stop = start + stop[0]

            if isinstance(stop, int):
                if stop < 0:
                    stop += width
                if stop < 0 or stop > width:
                    raise IndexError('stop index out of bounds')

                length = stop - start

                return 'const_slice', start, length

    return 'unknown', index


def dispatch_getitem(self, index):
    slice_type, *params = check_slice(len(self), index)

    def error_fn(*args):
        raise TypeError('unsupported index type')

    return getattr(self, '_getitem_' + slice_type, error_fn)(*params)
