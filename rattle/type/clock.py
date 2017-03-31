from .bool import Bool
from .bundle import Bundle, BundleSignal


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
            reset = 'sync'

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

    @property
    def _signal_class(self):
        return ClockSignal

    def __repr__(self):
        parts = []
        if self.reset != 'sync':
            parts.append('reset=%r' % self.reset)
        if self.gated:
            parts.append('gated=%r' % self.gated)
        return 'Clock(%s)' % ', '.join(parts)


class ClockSignal(BundleSignal):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.__context_stack = []

    def __enter__(self):
        from ..implicit import Implicit
        ctx = Implicit.bind('clk', self)
        ctx.__enter__()
        self.__context_stack.append(ctx)

    def __exit__(self, *exc):
        ctx = self.__context_stack.pop()
        return ctx.__exit__(*exc)
