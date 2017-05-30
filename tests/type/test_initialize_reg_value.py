from rattle.signal import *
from rattle.type import *
from rattle.bitvec import bv


def test_initialize_reg_bundle(sim_testbench):
    @sim_testbench
    def _testbench(self):
        self.bundle = Reg(Bundle(a=Bool, b=Bits(2), c=Flip(Bool)))

        yield

        assert self.bundle.a.value is False
        assert self.bundle.b.value == bv('00')
        assert self.bundle.c.value is False


def test_initialize_reg_enum(sim_testbench):
    @sim_testbench
    def _testbench(self):
        self.bundle = Reg(Enum(
            ('a', '111', dict(x=Bool)),
            ('b', '010')))

        yield

        assert self.bundle.packed.value == bv('0111')


def test_initialize_reg_vec(sim_testbench):
    @sim_testbench
    def _testbench(self):
        self.bundle = Reg(Vec(3, Bool))

        yield

        assert self.bundle.value == (False, False, False)
