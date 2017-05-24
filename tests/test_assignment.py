from rattle.type import *
from rattle.signal import *


def test_converting_assignment(module):
    self = module
    self.input = Input(UInt(10))
    self.wire = Wire(Bits(10))

    self.wire[:] = self.input


def test_const_converting_assignment(module):
    self = module
    self.wire = Wire(UInt(10))

    self.wire[:] = 23


def test_constant_assignment(sim_testbench):
    @sim_testbench
    def _testbench(self):
        self.wire = Wire(UInt(10))
        self.wire[:] = 23

        yield

        assert self.wire.value == 23
