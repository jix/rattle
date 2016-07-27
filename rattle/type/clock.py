from .type import *
from .bool import Bool
from .bundle import *


class Clock(Bundle):
    def __init__(self, has_reset='sync', is_gated=False, initial_reset=True):
        is_gated = bool(is_gated)
        initial_reset = bool(initial_reset)
        if has_reset != 'async':
            has_reset = 'sync' if bool(has_reset) else False

        self._has_reset = has_reset
        self._is_gated = is_gated
        self._initial_reset = initial_reset

        layout = {'clk': Bool}
        if has_reset:
            layout['reset'] = Bool
        if is_gated:
            layout['clk_en'] = Bool

        super().__init__(**layout)

    @property
    def has_reset(self):
        return self._has_reset

    @property
    def is_gated(self):
        return self._is_gated

    @property
    def initial_reset(self):
        return self._initial_reset

    @property
    def _signature_tuple(self):
        return (
            type(self), self.has_reset, self.is_gated, self.initial_reset)

    def __repr__(self):
        parts = []
        if self.has_reset != 'sync':
            parts.append('has_reset=%r' % self.has_reset)
        if self.is_gated:
            parts.append('is_gated=%r' % self.is_gated)
        if not self.initial_reset:
            parts.append('initial_reset=%r' % self.initial_reset)
        return 'Clock(%s)' % ', '.join(parts)
