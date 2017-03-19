from pytest import raises
from rattle.signal import *
from rattle.type import *
from rattle.error import ConversionNotImplemented


def test_bits_to_uint_generic(module):
    self = module
    self.bits_signal = Wire(Bits(8))
    self.uint_signal = self.bits_signal.as_uint()
    assert self.uint_signal.signal_type == UInt(8)
    self.uint_signal2 = UInt[self.bits_signal]
    assert self.uint_signal2.signal_type == UInt(8)


def test_bits_to_uint_generic_const(module):
    self = module
    self.bits_signal = Bits(8)[137]
    self.uint_signal = self.bits_signal.as_uint()
    assert self.uint_signal.signal_type == UInt(8)
    assert self.uint_signal.value == 137
    self.uint_signal2 = UInt[self.bits_signal]
    assert self.uint_signal2.signal_type == UInt(8)
    assert self.uint_signal2.value == 137


def test_bits_to_sint_generic(module):
    self = module
    self.bits_signal = Wire(Bits(8))
    self.sint_signal = self.bits_signal.as_sint()
    assert self.sint_signal.signal_type == SInt(8)
    self.sint_signal2 = SInt[self.bits_signal]
    assert self.sint_signal2.signal_type == SInt(8)


def test_bits_to_sint_generic_sign_clear_const(module):
    self = module
    self.bits_signal = Bits(8)[23]
    self.sint_signal = self.bits_signal.as_sint()
    assert self.sint_signal.signal_type == SInt(8)
    assert self.sint_signal.value == 23
    self.sint_signal2 = SInt[self.bits_signal]
    assert self.sint_signal2.signal_type == SInt(8)
    assert self.sint_signal2.value == 23


def test_bits_to_sint_generic_sign_set_const(module):
    self = module
    self.bits_signal = Bits(8)[137]
    self.sint_signal = self.bits_signal.as_sint()
    assert self.sint_signal.signal_type == SInt(8)
    assert self.sint_signal.value == -119
    self.sint_signal2 = SInt[self.bits_signal]
    assert self.sint_signal2.signal_type == SInt(8)
    assert self.sint_signal2.value == -119


def test_uint_to_bits_generic(module):
    self = module
    self.uint_signal = Wire(UInt(8))
    self.bits_signal = self.uint_signal.as_bits()
    assert self.bits_signal.signal_type == Bits(8)
    self.bits_signal2 = Bits[self.bits_signal]
    assert self.bits_signal2.signal_type == Bits(8)


def test_uint_to_bits_generic_const(module):
    self = module
    self.uint_signal = UInt(8)[137]
    self.bits_signal = self.uint_signal.as_bits()
    assert self.bits_signal.signal_type == Bits(8)
    assert self.bits_signal.value == 137
    self.bits_signal2 = Bits[self.bits_signal]
    assert self.bits_signal2.signal_type == Bits(8)
    assert self.bits_signal2.value == 137


def test_sint_to_bits_generic(module):
    self = module
    self.sint_signal = Wire(SInt(8))
    self.bits_signal = self.sint_signal.as_bits()
    assert self.bits_signal.signal_type == Bits(8)
    self.bits_signal2 = Bits[self.bits_signal]
    assert self.bits_signal2.signal_type == Bits(8)


def test_sint_to_bits_generic_const(module):
    self = module
    self.sint_signal = SInt(8)[-23]
    self.bits_signal = self.sint_signal.as_bits()
    assert self.bits_signal.signal_type == Bits(8)
    assert self.bits_signal.value == 233
    self.bits_signal2 = Bits[self.bits_signal]
    assert self.bits_signal2.signal_type == Bits(8)
    assert self.bits_signal2.value == 233


def test_uint_to_sint_generic(module):
    self = module
    self.uint_signal = Wire(UInt(8))
    self.sint_signal = self.uint_signal.as_sint()
    assert self.sint_signal.signal_type == SInt(9)
    self.sint_signal2 = SInt[self.uint_signal]
    assert self.sint_signal2.signal_type == SInt(9)


def test_uint_to_sint_generic_const(module):
    self = module
    self.uint_signal = UInt(8)[137]
    self.sint_signal = self.uint_signal.as_sint()
    assert self.sint_signal.signal_type == SInt(9)
    assert self.sint_signal.value == 137
    self.sint_signal2 = SInt[self.uint_signal]
    assert self.sint_signal2.signal_type == SInt(9)
    assert self.sint_signal2.value == 137


def test_invalid_sint_to_uint_generic(module):
    self = module
    self.sint_signal = Wire(SInt(8))
    with raises(ConversionNotImplemented):
        self.uint_signal = UInt[self.sint_signal]
