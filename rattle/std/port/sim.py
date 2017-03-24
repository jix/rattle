from collections import deque

from rattle.prelude import *
import rattle.sim as sim
from .port import Port


class SimSource(Module):
    def construct(self, payload_type):
        if payload_type.contains_flipped:
            raise TypeError(
                'SimSource does not support bidirectional payload types')

        self.source = Output(Port(payload_type))
        self.clk = Implicit('clk')

        # TODO Mark as simulation only

        self._items = deque()

    def append(self, item):
        self._items.append(item)
        self._update()

    def extend(self, items):
        self._items.extend(items)
        self._update()

    def replace(self, items):
        self._items = deque(items)
        self._update()

    def clear(self):
        self._items = deque()
        self._update()

    def sim_init(self):
        self._update()
        sim.always_on(self.clk, self._sim_clk)

    def _sim_clk(self):
        if self.source.active.value is True:
            self._items.popleft()
            self._update()

    def _update(self):
        if not sim.is_simulation():
            return
        if self._items:
            self.source.valid[:] = True
            self.source.payload[:] = self._items[0]
        else:
            self.source.valid[:] = False
            self.source.payload[:] = X


class SimSink(Module):
    def construct(self, payload_type):
        if payload_type.contains_flipped:
            raise TypeError(
                'SimSink does not support bidirectional payload types')

        self.sink = Input(Port(payload_type))
        self.clk = Implicit('clk')

        # TODO Mark as simulation only

        self.items = []
        self.callback = None

    def sim_init(self):
        self.sink.ready[:] = True
        sim.always_on(self.clk, self._sim_clk)

    def _sim_clk(self):
        if self.sink.active.value is True:
            payload = self.sink.payload.peek()
            if self.items is not None:
                self.items.append(payload)
            if self.callback is not None:
                self.callback(payload)  # pylint: disable=not-callable
