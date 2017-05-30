from rattle.prelude import *
from rattle.std.port import *
import rattle.sim as sim


def test_sim_sink_sim_source(sim_testbench):
    Type = Bundle(a=UInt(32), b=Bool)

    @sim_testbench
    def _testbench(self):
        self.source = SimSource(Type)
        self.sink = SimSink(Type)

        self.sink.sink[:] = self.source.source

        yield

        items = [
            dict(a=1, b=True),
            dict(a=2, b=False),
            dict(a=3, b=True),
            dict(a=4, b=True),
            dict(a=5, b=False),
            dict(a=6, b=False),
        ]

        self.source.replace(items)

        @sim.thread
        def _stop_source():
            for _ in range(4):
                yield self.clk
            self.source.run[:] = False

        yield self.clk

        self.sink.run[:] = False

        yield self.clk

        self.sink.run[:] = True

        for _ in range(8):
            yield self.clk

        self.source.run[:] = True

        for _ in range(4):
            yield self.clk

        self.sink.run[:] = False

        for _ in range(2):
            yield self.clk

        assert [x.value for x in self.sink.items] == items


def test_port_reg_initialization(sim_testbench):
    Type = Bundle(a=UInt(32), b=Bool)

    @sim_testbench
    def _testbench(self):
        self.reg = Reg(Port(Type))

        yield

        assert self.reg.payload.a.value is X
        assert self.reg.payload.b.value is X
        assert self.reg.ready.value is False
        assert self.reg.valid.value is False
