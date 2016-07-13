import pytest
from rattle.module import Module


@pytest.yield_fixture
def module():
    class TestModule(Module):
        def construct(self):
            pass
    mod = TestModule()
    with mod.reopen():
        yield mod
