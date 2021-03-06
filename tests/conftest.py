import pytest
from rattle.type import Clock
from rattle.signal import Input
from rattle.module import Module


@pytest.yield_fixture
def module():
    class TestModule(Module):
        def __init__(self):
            self.clk = Input(Clock()).as_implicit('clk')
    mod = TestModule()
    with mod.reopen():
        yield mod


def pytest_addoption(parser):
    parser.addoption(
        "--vcd", action="store_true",
        help="Generate vcd dumps of test simulation runs")


@pytest.fixture
def sim_runner(request):
    import rattle.sim as sim
    import os

    def run(tb, *args, **kwds):
        ctx = sim.SimContext(tb)
        if pytest.config.getoption("--vcd"):
            trace = sim.Trace()
            tb.trace(trace)

            try:
                os.mkdir('traces')
            except FileExistsError:
                pass
            ctx.dump_vcd_trace(trace, 'traces/%s.vcd' % request.node.name)

        ctx.run(*args, **kwds)
        ctx.reset()
    return run


@pytest.fixture
def sim_testbench(sim_runner):  # pylint: disable=redefined-outer-name
    import rattle.sim as sim

    def testbench(fn, *args, **kwds):
        class Testbench(Module):
            def __init__(self):
                self.clk = Input(Clock(reset='init')).as_implicit('clk')
                self._sim_testbench_fn = fn(self, *args, **kwds)
                next(self._sim_testbench_fn)

            def sim_init(self):
                sim.clock(self.clk, 10)
                yield from self._sim_testbench_fn
                sim.stop()

        sim_runner(Testbench())
    return testbench
