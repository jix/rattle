from .type import *
from .bool import Bool
from .bundle import *


_reset_modes = set([
    'sync', 'async', 'init', 'sync+init', 'async+init'])


class Clock(Bundle):
    def __init__(self, reset='sync', gated=False):
        gated = bool(gated)

        if isinstance(reset, str):
            if reset not in _reset_modes:
                raise ValueError('reset must be one of %s or False')
        else:
            reset = bool(reset)

        if reset is True:
            reset = 'sync'  # pylint: disable=redefined-variable-type

        self._reset = reset
        self._gated = gated

        layout = {'clk': Bool}
        if reset not in ('init', False):
            layout['reset'] = Bool
        if gated:
            layout['en'] = Bool

        super().__init__(**layout)

    @property
    def reset(self):
        return self._reset

    @property
    def gated(self):
        return self._gated

    @property
    def _signature_tuple(self):
        return (
            type(self), self.reset, self.gated)

    def __repr__(self):
        parts = []
        if self.reset != 'sync':
            parts.append('reset=%r' % self.reset)
        if self.gated:
            parts.append('gated=%r' % self.gated)
        return 'Clock(%s)' % ', '.join(parts)
