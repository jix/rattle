import pytest
from rattle.type import Clock
from rattle.signal import Input
from rattle.module import Module


@pytest.yield_fixture
def module():
    class TestModule(Module):
        def construct(self):
            self.clk = Input(Clock()).as_implicit('clk')
    mod = TestModule()
    with mod.reopen():
        yield mod
