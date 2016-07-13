from nose.tools import *
from rattle.signal import *
from rattle.type import *
from rattle.error import *
from tests.module import construct_as_module


# TODO Add simulation tests for conversions when ready
@construct_as_module
def test_bits_to_uint_generic(self):
    self.bits_signal = Wire(Bits(8))
    self.uint_signal = self.bits_signal.as_uint()
    eq_(self.uint_signal.signal_type, UInt(8))
    self.uint_signal = UInt[self.bits_signal]
    eq_(self.uint_signal.signal_type, UInt(8))


@construct_as_module
def test_bits_to_sint_generic(self):
    self.bits_signal = Wire(Bits(8))
    self.sint_signal = self.bits_signal.as_sint()
    eq_(self.sint_signal.signal_type, SInt(8))
    self.sint_signal = SInt[self.bits_signal]
    eq_(self.sint_signal.signal_type, SInt(8))


@construct_as_module
def test_bits_to_uint_sized(self):
    self.bits_signal = Wire(Bits(8))
    self.uint_signal = UInt(8)[self.bits_signal]
    eq_(self.uint_signal.signal_type, UInt(8))


@construct_as_module
def test_bits_to_sint_sized(self):
    self.bits_signal = Wire(Bits(8))
    self.sint_signal = SInt(8)[self.bits_signal]
    eq_(self.sint_signal.signal_type, SInt(8))


@construct_as_module
def test_bits_to_uint_extending(self):
    self.bits_signal = Wire(Bits(8))
    self.uint_signal = UInt(16)[self.bits_signal]
    eq_(self.uint_signal.signal_type, UInt(16))


@construct_as_module
def test_bits_to_sint_extending(self):
    self.bits_signal = Wire(Bits(8))
    self.sint_signal = SInt(16)[self.bits_signal]
    eq_(self.sint_signal.signal_type, SInt(16))


@raises(ConversionNotImplemented)
@construct_as_module
def test_bits_to_uint_invalid_truncate(self):
    self.bits_signal = Wire(Bits(8))
    self.uint_signal = UInt(4)[self.bits_signal]


@raises(ConversionNotImplemented)
@construct_as_module
def test_bits_to_sint_invalid_truncate(self):
    self.bits_signal = Wire(Bits(8))
    self.sint_signal = SInt(4)[self.bits_signal]


@construct_as_module
def test_uint_to_bits_generic(self):
    self.uint_signal = Wire(UInt(8))
    self.bits_signal = self.uint_signal.as_bits()
    eq_(self.bits_signal.signal_type, Bits(8))
    self.bits_signal = Bits[self.bits_signal]
    eq_(self.bits_signal.signal_type, Bits(8))


@construct_as_module
def test_sint_to_bits_generic(self):
    self.sint_signal = Wire(SInt(8))
    self.bits_signal = self.sint_signal.as_bits()
    eq_(self.bits_signal.signal_type, Bits(8))
    self.bits_signal = Bits[self.bits_signal]
    eq_(self.bits_signal.signal_type, Bits(8))


@construct_as_module
def test_uint_to_bits_sized(self):
    self.uint_signal = Wire(UInt(8))
    self.bits_signal = Bits(8)[self.uint_signal]
    eq_(self.bits_signal.signal_type, Bits(8))


@construct_as_module
def test_sint_to_bits_sized(self):
    self.sint_signal = Wire(SInt(8))
    self.bits_signal = Bits(8)[self.sint_signal]
    eq_(self.bits_signal.signal_type, Bits(8))


@construct_as_module
def test_uint_to_bits_extending(self):
    self.uint_signal = Wire(UInt(8))
    self.bits_signal = Bits(16)[self.uint_signal]
    eq_(self.bits_signal.signal_type, Bits(16))


@raises(NotImplementedError)  # TODO Test when implementation is ready
@construct_as_module
def test_sint_to_bits_extending(self):
    self.sint_signal = Wire(SInt(8))
    self.bits_signal = Bits(16)[self.sint_signal]
    eq_(self.bits_signal.signal_type, Bits(16))


@raises(ConversionNotImplemented)
@construct_as_module
def test_uint_to_bits_invalid_truncate(self):
    self.uint_signal = Wire(UInt(8))
    self.bits_signal = Bits(4)[self.uint_signal]


@raises(ConversionNotImplemented)
@construct_as_module
def test_sint_to_bits_invalid_truncate(self):
    self.sint_signal = Wire(SInt(8))
    self.bits_signal = Bits(4)[self.sint_signal]


@construct_as_module
def test_uint_to_sint_generic(self):
    self.uint_signal = Wire(UInt(8))
    self.sint_signal = self.uint_signal.as_sint()
    eq_(self.sint_signal.signal_type, SInt(9))
    self.sint_signal = SInt[self.uint_signal]
    eq_(self.sint_signal.signal_type, SInt(9))


@construct_as_module
def test_uint_to_sint_sized(self):
    self.uint_signal = Wire(UInt(8))
    self.sint_signal = SInt(9)[self.uint_signal]
    eq_(self.sint_signal.signal_type, SInt(9))


@construct_as_module
def test_uint_to_sint_extending(self):
    self.uint_signal = Wire(UInt(8))
    self.sint_signal = SInt(16)[self.uint_signal]
    eq_(self.sint_signal.signal_type, SInt(16))


@raises(ConversionNotImplemented)
@construct_as_module
def test_uint_to_sint_invalid_truncate(self):
    self.uint_signal = Wire(UInt(8))
    self.sint_signal = SInt(8)[self.uint_signal]


@raises(ConversionNotImplemented)
@construct_as_module
def test_invalid_sint_to_uint_generic(self):
    self.sint_signal = Wire(SInt(8))
    self.uint_signal = UInt[self.sint_signal]


@raises(ConversionNotImplemented)
@construct_as_module
def test_invalid_sint_to_uint_sized(self):
    self.sint_signal = Wire(SInt(8))
    self.uint_signal = UInt(16)[self.sint_signal]
