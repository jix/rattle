from .signal import Signal
from .type.clock import Clock
from .implicit import Implicit
from . import context


class Reg(Signal):
    def __init__(self, signal_type, *, clk=None):
        # TODO Allow construction with automatic assignment
        # TODO Allow optional enable for automatic assignment

        if clk is None:
            clk = Implicit('clk')
        if not isinstance(clk.signal_type, Clock):
            raise TypeError('clk must be of signal type Clock')
        clk._access_read()
        self._clk = clk

        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module,
            rmodule=module)

    @property
    def clk(self):
        return self._clk

    def __repr__(self):
        return "Reg(%r)" % (self.signal_type)
