from nose.tools import *
from rattle.signal import *
from rattle.type import *
from rattle.error import *
from tests.module import construct_as_module


@construct_as_module
def test_bits_to_uint_generic(self):
    self.bits_signal = Bits(8)[137]
    self.uint_signal = self.bits_signal.as_uint()
    eq_(self.uint_signal.signal_type, UInt(8))
    eq_(self.uint_signal.value, 137)
    self.uint_signal = UInt[self.bits_signal]
    eq_(self.uint_signal.signal_type, UInt(8))
    eq_(self.uint_signal.value, 137)


@construct_as_module
def test_bits_to_sint_generic_sign_clear(self):
    self.bits_signal = Bits(8)[23]
    self.sint_signal = self.bits_signal.as_sint()
    eq_(self.sint_signal.signal_type, SInt(8))
    eq_(self.sint_signal.value, 23)
    self.sint_signal = SInt[self.bits_signal]
    eq_(self.sint_signal.signal_type, SInt(8))
    eq_(self.sint_signal.value, 23)


@construct_as_module
def test_bits_to_sint_generic_sign_set(self):
    self.bits_signal = Bits(8)[137]
    self.sint_signal = self.bits_signal.as_sint()
    eq_(self.sint_signal.signal_type, SInt(8))
    eq_(self.sint_signal.value, -119)
    self.sint_signal = SInt[self.bits_signal]
    eq_(self.sint_signal.signal_type, SInt(8))
    eq_(self.sint_signal.value, -119)


@construct_as_module
def test_bits_to_uint_extending(self):
    self.bits_signal = Bits(8)[137]
    self.uint_signal = UInt(16)[self.bits_signal]
    eq_(self.uint_signal.signal_type, UInt(16))
    eq_(self.uint_signal.value, 137)


@construct_as_module
def test_bits_to_sint_extending(self):
    self.bits_signal = Bits(8)[137]
    self.sint_signal = SInt(16)[self.bits_signal]
    eq_(self.sint_signal.signal_type, SInt(16))
    eq_(self.sint_signal.value, 137)


@construct_as_module
def test_uint_to_bits_generic(self):
    self.uint_signal = UInt(8)[137]
    self.bits_signal = self.uint_signal.as_bits()
    eq_(self.bits_signal.signal_type, Bits(8))
    eq_(self.bits_signal.value, 137)
    self.bits_signal = Bits[self.bits_signal]
    eq_(self.bits_signal.signal_type, Bits(8))
    eq_(self.bits_signal.value, 137)


@construct_as_module
def test_sint_to_bits_generic(self):
    self.sint_signal = SInt(8)[-23]
    self.bits_signal = self.sint_signal.as_bits()
    eq_(self.bits_signal.signal_type, Bits(8))
    eq_(self.bits_signal.value, 233)
    self.bits_signal = Bits[self.bits_signal]
    eq_(self.bits_signal.signal_type, Bits(8))
    eq_(self.bits_signal.value, 233)


@construct_as_module
def test_uint_to_sint_generic(self):
    self.uint_signal = UInt(8)[137]
    self.sint_signal = self.uint_signal.as_sint()
    eq_(self.sint_signal.signal_type, SInt(9))
    eq_(self.sint_signal.value, 137)
    self.sint_signal = SInt[self.uint_signal]
    eq_(self.sint_signal.signal_type, SInt(9))
    eq_(self.sint_signal.value, 137)
