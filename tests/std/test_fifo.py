from rattle.prelude import *
from rattle.std.port import SimSource, SimSink
from rattle.std.fifo import *
import rattle.sim as sim


def test_fifo(sim_testbench):
    Type = Bundle(a=UInt(32), b=Bool)

    @sim_testbench
    def _testbench(self):
        self.source = SimSource(Type)
        self.sink = SimSink(Type)
        self.fifo = Fifo(Type, 4)

        self.fifo.sink[:] = self.source.source
        self.sink.sink[:] = self.fifo.source

        yield

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

        for _ in range(40):
            yield self.clk

        assert [x.value for x in self.sink.items] == items
