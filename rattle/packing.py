from contextlib import contextmanager
from .type import Bits, Bundle, bundle, Flip
from .signal import Signal


class Packer:
    def __init__(self):
        self._fwd = []
        self._bwd = []

    def pack(self, signal):
        self._fwd.append(signal)

    @contextmanager
    def flip(self):
        self._fwd, self._bwd = self._bwd, self._fwd
        yield
        self._fwd, self._bwd = self._bwd, self._fwd

    def packed_signal(self):
        fwd = Bits.concat(*self._fwd)
        bwd = Bits.concat(*self._bwd)

        if bwd.width == 0:
            return fwd
        else:
            return bundle(fwd=fwd, bwd=bwd.flipped)


class Unpacker:
    def __init__(self, signal):
        if Signal.isinstance(signal, Bits):
            self._fwd = signal
            self._bwd = Bits['']
        elif (
                Signal.isinstance(signal, Bundle) and
                isinstance(
                    signal.signal_type.fields.get('fwd'), Bits) and
                isinstance(
                    signal.signal_type.fields.get('bwd'), Flip) and
                len(signal.signal_type.fields) == 2 and
                Signal.isinstance(signal['bwd'], Bits)):
            self._fwd = signal.fwd
            self._bwd = signal.bwd
        else:
            raise TypeError('cannot unpack %r' % signal)

        self._fwd_pos = 0
        self._bwd_pos = 0

    def unpack(self, width):
        end = self._fwd_pos + width
        result = self._fwd[self._fwd_pos:end]
        self._fwd_pos = end
        return result

    @contextmanager
    def flip(self):
        self._fwd, self._bwd = self._bwd, self._fwd
        self._fwd_pos, self._bwd_pos = self._bwd_pos, self._fwd_pos
        yield
        self._fwd, self._bwd = self._bwd, self._fwd
        self._fwd_pos, self._bwd_pos = self._bwd_pos, self._fwd_pos
