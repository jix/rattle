from rattle.prelude import *
from rattle.std.port import *
import rattle.sim as sim


def test_sim_sink_sim_source(sim_runner):
    Type = Bundle(a=UInt(32), b=Bool)

    class TB(Module):
        def construct(self):
            self.clk = Input(Clock(reset='init')).as_implicit('clk')

            self.source = SimSource(Type)
            self.sink = SimSink(Type)

            self.sink.sink[:] = self.source.source

        def sim_init(self):
            sim.clock(self.clk, 10)

            items = [
                dict(a=1, b=True),
                dict(a=2, b=False),
                dict(a=3, b=True),
                dict(a=4, b=True),
                dict(a=5, b=False),
                dict(a=6, b=False),
            ]

            self.source.replace(items[:4])

            yield self.clk

            self.sink.sink.ready[:] = False

            yield self.clk

            self.sink.sink.ready[:] = True

            for _ in range(8):
                yield self.clk

            self.source.extend(items[4:])

            for _ in range(4):
                yield self.clk

            self.sink.sink.ready[:] = False

            for _ in range(2):
                yield self.clk

            assert [x.value for x in self.sink.items] == items

            sim.stop()

    sim_runner(TB())
