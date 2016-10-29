def check_slice(width, index):
    if index == slice(None, None, None):
        return 'all', None
    elif isinstance(index, int):
        if index < 0:
            index += width
        if index < 0 or index >= width:
            raise IndexError('index out of bounds')
        return 'const_index', index
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

                return 'const_slice', (start, length)

    return 'unknown', index
