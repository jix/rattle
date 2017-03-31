import pytest
from rattle.prelude import *
from rattle.std.port import SimSource, SimSink
from rattle.std.cdc import AsyncFifo
import rattle.sim as sim


@pytest.mark.parametrize("period", [3, 5, 8, 9, 10, 11, 12, 15, 20])
def test_async_fifo(sim_testbench, period):
    Type = Bundle(a=UInt(32), b=Bool)

    @sim_testbench
    def _testbench(self):
        self.clk2 = Input(Clock(reset='init'))

        with self.clk2:
            self.source = SimSource(Type)
        self.sink = SimSink(Type)

        self.fifo = AsyncFifo(Type, 4, sink_clk=self.clk2, source_clk=self.clk)

        self.fifo.sink[:] = self.source.source
        self.sink.sink[:] = self.fifo.source

        yield

        sim.clock(self.clk2, period)

        items = [
            dict(a=a, b=bin(a).count('1') & 1)
            for a in range(20)
        ]

        self.source.replace(items)

        @sim.thread
        def _toggle_source():
            self.source.run[:] = True
            for _ in range(8):
                yield self.clk
            for _ in range(2):
                yield self.clk
                self.source.run[:] = False
                yield self.clk
                self.source.run[:] = True
            yield self.clk
            for _ in range(6):
                yield self.clk
                self.source.run[:] = False
                yield self.clk
                self.source.run[:] = True

        @sim.thread
        def _toggle_sink():
            for _ in range(8):
                yield self.clk
                self.sink.run[:] = False
                yield self.clk
                self.sink.run[:] = True

        for _ in range(max(40, 40 * period // 10)):
            yield self.clk

        assert [x.value for x in self.sink.items] == items
