from pytest import raises
from rattle.signal import *
from rattle.type import *
from rattle.error import ConversionNotImplemented
from rattle.bitvec import bv


def test_int_to_bits_exact(module):
    self = module
    self.bits_8 = Wire(Bits(8))
    self.bits_12 = Wire(Bits(12))

    self.uint_8 = Wire(UInt(8))
    self.sint_12 = Wire(SInt(12))

    self.bits_8[:] = self.uint_8
    self.bits_12[:] = self.sint_12


def test_int_to_bits_exact_const():
    assert Bits(8)[UInt(8)[0b10101010]].value == bv('10101010')
    assert Bits(12)[SInt(12)[-0b10101010]].value == bv('111101010110')


def test_int_to_bits_truncate(module):
    self = module
    self.bits_4 = Wire(Bits(4))
    self.bits_8 = Wire(Bits(8))

    self.uint_8 = Wire(UInt(8))
    self.sint_12 = Wire(SInt(12))

    self.bits_4[:] = self.uint_8
    self.bits_8[:] = self.sint_12


def test_int_to_bits_truncate_const():
    assert Bits(4)[UInt(8)[0b10101010]].value == bv('1010')
    assert Bits(8)[SInt(12)[-0b10101010]].value == bv('01010110')


def test_int_to_bits_extend(module):
    self = module
    self.bits_12 = Wire(Bits(12))
    self.bits_16 = Wire(Bits(16))

    self.uint_8 = Wire(UInt(8))
    self.sint_12 = Wire(SInt(12))

    self.bits_12[:] = self.uint_8
    self.bits_16[:] = self.sint_12


def test_int_to_bits_extend_const():
    assert Bits(12)[UInt(8)[0b10101010]].value == bv('000010101010')
    assert Bits(16)[SInt(12)[-0b10101010]].value == bv('1111111101010110')


def test_int_to_int_exact(module):
    self = module
    self.t_uint_8 = Wire(UInt(8))
    self.t_sint_8 = Wire(SInt(8))
    self.t_uint_12 = Wire(UInt(12))
    self.t_sint_12 = Wire(SInt(12))

    self.uint_8 = Wire(UInt(8))
    self.sint_12 = Wire(SInt(12))

    self.t_uint_8[:] = self.uint_8
    self.t_sint_8[:] = self.uint_8
    self.t_uint_12[:] = self.sint_12
    self.t_sint_12[:] = self.sint_12


def test_int_to_int_exact_const():
    assert UInt(8)[UInt(8)[0b10101010]].value == 0b10101010
    assert SInt(8)[UInt(8)[0b10101010]].value == -0b1010110
    assert UInt(12)[SInt(12)[-0b10101010]].value == 0b111101010110
    assert SInt(12)[SInt(12)[-0b10101010]].value == -0b10101010


def test_int_to_int_truncate(module):
    self = module
    self.t_uint_4 = Wire(UInt(4))
    self.t_sint_4 = Wire(SInt(4))
    self.t_uint_8 = Wire(UInt(8))
    self.t_sint_8 = Wire(SInt(8))

    self.uint_8 = Wire(UInt(8))
    self.sint_12 = Wire(SInt(12))

    self.t_uint_4[:] = self.uint_8
    self.t_sint_4[:] = self.uint_8
    self.t_uint_8[:] = self.sint_12
    self.t_sint_8[:] = self.sint_12


def test_int_to_int_truncate_const():
    assert UInt(4)[UInt(8)[0b10101010]].value == 0b1010
    assert SInt(4)[UInt(8)[0b10101010]].value == -0b0110
    assert UInt(8)[SInt(12)[-0b10101010]].value == 0b01010110
    assert SInt(8)[SInt(12)[-0b10101010]].value == 0b01010110


def test_int_to_int_extend(module):
    self = module
    self.t_uint_12 = Wire(UInt(12))
    self.t_sint_12 = Wire(SInt(12))
    self.t_uint_16 = Wire(UInt(16))
    self.t_sint_16 = Wire(SInt(16))

    self.uint_8 = Wire(UInt(8))
    self.sint_12 = Wire(SInt(12))

    self.t_uint_12[:] = self.uint_8
    self.t_sint_12[:] = self.uint_8
    self.t_uint_16[:] = self.sint_12
    self.t_sint_16[:] = self.sint_12


def test_int_to_int_extend_const():
    assert UInt(12)[UInt(8)[0b10101010]].value == 0b10101010
    assert SInt(12)[UInt(8)[0b10101010]].value == 0b10101010
    assert UInt(16)[SInt(12)[-0b10101010]].value == 0b1111111101010110
    assert SInt(16)[SInt(12)[-0b10101010]].value == -0b10101010


def test_bits_to_int_invalid_implicit(module):
    self = module
    self.uint_12 = Wire(UInt(12))
    self.sint_12 = Wire(SInt(12))
    self.bits_12 = Wire(Bits(12))

    with raises(ConversionNotImplemented):
        self.uint_12[:] = self.bits_12
    with raises(ConversionNotImplemented):
        self.sint_12[:] = self.bits_12


def test_bits_to_int_exact_explicit(module):
    self = module
    self.uint_8 = Wire(UInt(8))
    self.sint_12 = Wire(SInt(12))

    self.bits_8 = Wire(Bits(8))
    self.bits_12 = Wire(Bits(12))

    self.uint_8[:] = UInt(8)[self.bits_8]
    self.sint_12[:] = SInt(12)[self.bits_12]


def test_bits_to_int_exact_const():
    assert UInt(8)[Bits(8)['10101010']].value == 0b10101010
    assert SInt(12)[Bits(12)['111101010110']].value == -0b10101010


def test_bits_to_int_truncate_explicit(module):
    self = module
    self.uint_4 = Wire(UInt(4))
    self.sint_8 = Wire(SInt(8))

    self.bits_8 = Wire(Bits(8))
    self.bits_12 = Wire(Bits(12))

    self.uint_4[:] = UInt(4)[self.bits_8]
    self.sint_8[:] = SInt(8)[self.bits_12]


def test_bits_to_int_truncate_const():
    assert UInt(4)[Bits(8)['10101010']].value == 0b1010
    assert SInt(8)[Bits(12)['111101010110']].value == 0b1010110


def test_bits_to_int_extend_explicit(module):
    self = module
    self.uint_12 = Wire(UInt(12))
    self.sint_16 = Wire(SInt(16))

    self.bits_8 = Wire(Bits(8))
    self.bits_12 = Wire(Bits(12))

    self.uint_12[:] = UInt(12)[self.bits_8]
    self.sint_16[:] = SInt(16)[self.bits_12]


def test_bits_to_int_extend_const():
    assert UInt(12)[Bits(8)['10101010']].value == 0b10101010
    assert SInt(16)[Bits(12)['111101010110']].value == 0b111101010110


def test_bits_to_bits_invalid_truncate(module):
    self = module
    self.bits_8 = Wire(Bits(8))
    self.bits_4 = Wire(Bits(4))

    with raises(ConversionNotImplemented):
        self.bits_4[:] = self.bits_8


def test_bits_to_bits_invalid_extend(module):
    self = module
    self.bits_4 = Wire(Bits(4))
    self.bits_8 = Wire(Bits(8))
    with raises(ConversionNotImplemented):
        self.bits_8[:] = self.bits_4
