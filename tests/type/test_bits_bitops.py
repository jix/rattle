from rattle.module import *
from rattle.signal import *
from rattle.type import *


def test_const_negate():
    assert (~Bits(12)[1337]).value == 2758
    assert (~UInt(12)[1337]).value == 2758
    assert (~SInt(12)[1337]).value == -1338
    assert (~SInt(12)[-1337]).value == 1336


def test_const_binops():
    assert (Bits(4)[12] & Bits(4)[10]).value == 8
    assert (Bits(4)[12] | Bits(4)[10]).value == 14
    assert (Bits(4)[12] ^ Bits(4)[10]).value == 6


def test_binops_coercion(module):
    module.uint4 = Wire(UInt(4))
    module.sint4 = Wire(SInt(4))
    module.bits4 = Wire(Bits(4))

    assert (module.uint4 & module.sint4).signal_type == SInt(5)
    assert (module.uint4 | module.bits4).signal_type == Bits(4)
    assert (module.sint4 ^ module.bits4).signal_type == Bits(4)
