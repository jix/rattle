from rattle.signal import *
from rattle.type import *
from rattle.error import *


def test_bits_to_uint_generic(module):
    module.bits_signal = Bits(8)[137]
    module.uint_signal = module.bits_signal.as_uint()
    assert module.uint_signal.signal_type == UInt(8)
    assert module.uint_signal.value == 137
    module.uint_signal = UInt[module.bits_signal]
    assert module.uint_signal.signal_type == UInt(8)
    assert module.uint_signal.value == 137


def test_bits_to_sint_generic_sign_clear(module):
    module.bits_signal = Bits(8)[23]
    module.sint_signal = module.bits_signal.as_sint()
    assert module.sint_signal.signal_type == SInt(8)
    assert module.sint_signal.value == 23
    module.sint_signal = SInt[module.bits_signal]
    assert module.sint_signal.signal_type == SInt(8)
    assert module.sint_signal.value == 23


def test_bits_to_sint_generic_sign_set(module):
    module.bits_signal = Bits(8)[137]
    module.sint_signal = module.bits_signal.as_sint()
    assert module.sint_signal.signal_type == SInt(8)
    assert module.sint_signal.value == -119
    module.sint_signal = SInt[module.bits_signal]
    assert module.sint_signal.signal_type == SInt(8)
    assert module.sint_signal.value == -119


def test_bits_to_uint_extending(module):
    module.bits_signal = Bits(8)[137]
    module.uint_signal = UInt(16)[module.bits_signal]
    assert module.uint_signal.signal_type == UInt(16)
    assert module.uint_signal.value == 137


def test_bits_to_sint_extending(module):
    module.bits_signal = Bits(8)[137]
    module.sint_signal = SInt(16)[module.bits_signal]
    assert module.sint_signal.signal_type == SInt(16)
    assert module.sint_signal.value == 137


def test_uint_to_bits_generic(module):
    module.uint_signal = UInt(8)[137]
    module.bits_signal = module.uint_signal.as_bits()
    assert module.bits_signal.signal_type == Bits(8)
    assert module.bits_signal.value == 137
    module.bits_signal = Bits[module.bits_signal]
    assert module.bits_signal.signal_type == Bits(8)
    assert module.bits_signal.value == 137


def test_sint_to_bits_generic(module):
    module.sint_signal = SInt(8)[-23]
    module.bits_signal = module.sint_signal.as_bits()
    assert module.bits_signal.signal_type == Bits(8)
    assert module.bits_signal.value == 233
    module.bits_signal = Bits[module.bits_signal]
    assert module.bits_signal.signal_type == Bits(8)
    assert module.bits_signal.value == 233


def test_uint_to_sint_generic(module):
    module.uint_signal = UInt(8)[137]
    module.sint_signal = module.uint_signal.as_sint()
    assert module.sint_signal.signal_type == SInt(9)
    assert module.sint_signal.value == 137
    module.sint_signal = SInt[module.uint_signal]
    assert module.sint_signal.signal_type == SInt(9)
    assert module.sint_signal.value == 137
