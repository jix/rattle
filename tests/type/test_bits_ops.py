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


# TODO Add simulation tests when ready

def test_binops_coercion(module):
    module.uint4 = Wire(UInt(4))
    module.sint4 = Wire(SInt(4))
    module.bits4 = Wire(Bits(4))

    assert (module.uint4 & module.sint4).signal_type == SInt(5)
    assert (module.uint4 | module.bits4).signal_type == Bits(4)
    assert (module.sint4 ^ module.bits4).signal_type == Bits(4)


def test_const_repeat():
    assert Bits(4)[0xA].repeat(4).value == 0xAAAA


def test_bits_const_indexing(module):
    self = module
    self.bits = Wire(Bits(4))
    self.bool_a = Wire(Bool)
    self.bool_b = Wire(Bool)
    assert self.bits[0].signal_type == Bool
    self.bits[1][:] = self.bool_a
    assert self.bits[-1].signal_type == Bool
    self.bits[-2][:] = self.bool_b


def test_bits_bit_access_const():
    my_bits = Bits(8)[0b10010110]
    assert my_bits[0].value is False
    assert my_bits[1].value is True
    assert my_bits[-1].value is True


def test_bits_const_slicing(module):
    self = module
    self.bits1 = Wire(Bits(4))
    self.bits2 = Wire(Bits(8))
    assert self.bits1[0:2].signal_type == Bits(2)
    self.bits1[0:2][:] = self.bits2[2:4]
    assert self.bits1[-3:].signal_type == Bits(3)
    self.bits1[-3:][:] = self.bits2[5:]
    assert self.bits1[1:[2]].signal_type == Bits(2)
    self.bits1[1:[2]][:] = self.bits2[5:[2]]


def test_bits_slice_access_const():
    my_bits = Bits(8)[0b10010110]
    assert my_bits[0:3].value == 0b110
    assert my_bits[4:].value == 0b1001
    assert my_bits[:4].value == 0b0110
    assert my_bits[2:[4]].value == 0b0101
