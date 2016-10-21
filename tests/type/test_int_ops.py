from rattle.module import *
from rattle.signal import *
from rattle.type import *


def test_and_coercion(module):
    self = module
    self.uint4 = Wire(UInt(4))
    self.sint4 = Wire(SInt(4))
    self.uint8 = Wire(UInt(8))
    self.sint8 = Wire(SInt(8))

    assert (self.uint4 & self.uint4).signal_type == UInt(4)
    assert (self.uint4 & self.sint4).signal_type == UInt(4)
    assert (self.uint4 & self.uint8).signal_type == UInt(4)
    assert (self.uint4 & self.sint8).signal_type == UInt(4)
    assert (self.sint4 & self.sint4).signal_type == SInt(4)
    assert (self.sint4 & self.uint8).signal_type == UInt(8)
    assert (self.sint4 & self.sint8).signal_type == SInt(8)


def test_or_coercion(module):
    self = module
    self.uint4 = Wire(UInt(4))
    self.sint4 = Wire(SInt(4))
    self.uint8 = Wire(UInt(8))
    self.sint8 = Wire(SInt(8))

    assert (self.uint4 | self.uint4).signal_type == UInt(4)
    assert (self.uint4 | self.sint4).signal_type == SInt(5)
    assert (self.uint4 | self.uint8).signal_type == UInt(8)
    assert (self.uint4 | self.sint8).signal_type == SInt(8)
    assert (self.sint4 | self.sint4).signal_type == SInt(4)
    assert (self.sint4 | self.uint8).signal_type == SInt(9)
    assert (self.sint4 | self.sint8).signal_type == SInt(8)


def test_xor_coercion(module):
    self = module
    self.uint4 = Wire(UInt(4))
    self.sint4 = Wire(SInt(4))
    self.uint8 = Wire(UInt(8))
    self.sint8 = Wire(SInt(8))

    assert (self.uint4 ^ self.uint4).signal_type == UInt(4)
    assert (self.uint4 ^ self.sint4).signal_type == SInt(5)
    assert (self.uint4 ^ self.uint8).signal_type == UInt(8)
    assert (self.uint4 ^ self.sint8).signal_type == SInt(8)
    assert (self.sint4 ^ self.sint4).signal_type == SInt(4)
    assert (self.sint4 ^ self.uint8).signal_type == SInt(9)
    assert (self.sint4 ^ self.sint8).signal_type == SInt(8)


def test_negation(module):
    self = module
    self.uint4 = Wire(UInt(4))
    self.sint4 = Wire(SInt(4))

    assert (~self.uint4).signal_type == SInt(5)
    assert (~self.sint4).signal_type == SInt(4)


def test_negation_const():
    assert (~UInt(12)[1337]).value == ~1337
    assert (~SInt(12)[1337]).value == ~1337
    assert (~SInt(12)[-1337]).value == ~-1337
