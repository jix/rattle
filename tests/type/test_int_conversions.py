from pytest import raises
from rattle.signal import *
from rattle.type import *
from rattle.error import *


# TODO Add simulation tests for conversions when ready
def test_bits_to_uint_generic(module):
    module.bits_signal = Wire(Bits(8))
    module.uint_signal = module.bits_signal.as_uint()
    assert module.uint_signal.signal_type == UInt(8)
    module.uint_signal = UInt[module.bits_signal]
    assert module.uint_signal.signal_type == UInt(8)


def test_bits_to_sint_generic(module):
    module.bits_signal = Wire(Bits(8))
    module.sint_signal = module.bits_signal.as_sint()
    assert module.sint_signal.signal_type == SInt(8)
    module.sint_signal = SInt[module.bits_signal]
    assert module.sint_signal.signal_type == SInt(8)


def test_bits_to_uint_sized(module):
    module.bits_signal = Wire(Bits(8))
    module.uint_signal = UInt(8)[module.bits_signal]
    assert module.uint_signal.signal_type == UInt(8)


def test_bits_to_sint_sized(module):
    module.bits_signal = Wire(Bits(8))
    module.sint_signal = SInt(8)[module.bits_signal]
    assert module.sint_signal.signal_type == SInt(8)


def test_bits_to_uint_extending(module):
    module.bits_signal = Wire(Bits(8))
    module.uint_signal = UInt(16)[module.bits_signal]
    assert module.uint_signal.signal_type == UInt(16)


def test_bits_to_sint_extending(module):
    module.bits_signal = Wire(Bits(8))
    module.sint_signal = SInt(16)[module.bits_signal]
    assert module.sint_signal.signal_type == SInt(16)


def test_bits_to_uint_invalid_truncate(module):
    module.bits_signal = Wire(Bits(8))
    with raises(ConversionNotImplemented):
        module.uint_signal = UInt(4)[module.bits_signal]


def test_bits_to_sint_invalid_truncate(module):
    module.bits_signal = Wire(Bits(8))
    with raises(ConversionNotImplemented):
        module.sint_signal = SInt(4)[module.bits_signal]


def test_uint_to_bits_generic(module):
    module.uint_signal = Wire(UInt(8))
    module.bits_signal = module.uint_signal.as_bits()
    assert module.bits_signal.signal_type == Bits(8)
    module.bits_signal = Bits[module.bits_signal]
    assert module.bits_signal.signal_type == Bits(8)


def test_sint_to_bits_generic(module):
    module.sint_signal = Wire(SInt(8))
    module.bits_signal = module.sint_signal.as_bits()
    assert module.bits_signal.signal_type == Bits(8)
    module.bits_signal = Bits[module.bits_signal]
    assert module.bits_signal.signal_type == Bits(8)


def test_uint_to_bits_sized(module):
    module.uint_signal = Wire(UInt(8))
    module.bits_signal = Bits(8)[module.uint_signal]
    assert module.bits_signal.signal_type == Bits(8)


def test_sint_to_bits_sized(module):
    module.sint_signal = Wire(SInt(8))
    module.bits_signal = Bits(8)[module.sint_signal]
    assert module.bits_signal.signal_type == Bits(8)


def test_uint_to_bits_extending(module):
    module.uint_signal = Wire(UInt(8))
    module.bits_signal = Bits(16)[module.uint_signal]
    assert module.bits_signal.signal_type == Bits(16)


def test_sint_to_bits_extending(module):
    with raises(NotImplementedError):  # TODO Test when implementation is ready
        module.sint_signal = Wire(SInt(8))
        module.bits_signal = Bits(16)[module.sint_signal]
        assert module.bits_signal.signal_type == Bits(16)


def test_uint_to_bits_invalid_truncate(module):
    module.uint_signal = Wire(UInt(8))
    with raises(ConversionNotImplemented):
        module.bits_signal = Bits(4)[module.uint_signal]


def test_sint_to_bits_invalid_truncate(module):
    module.sint_signal = Wire(SInt(8))
    with raises(ConversionNotImplemented):
        module.bits_signal = Bits(4)[module.sint_signal]


def test_uint_to_sint_generic(module):
    module.uint_signal = Wire(UInt(8))
    module.sint_signal = module.uint_signal.as_sint()
    assert module.sint_signal.signal_type == SInt(9)
    module.sint_signal = SInt[module.uint_signal]
    assert module.sint_signal.signal_type == SInt(9)


def test_uint_to_sint_sized(module):
    module.uint_signal = Wire(UInt(8))
    module.sint_signal = SInt(9)[module.uint_signal]
    assert module.sint_signal.signal_type == SInt(9)


def test_uint_to_sint_extending(module):
    module.uint_signal = Wire(UInt(8))
    module.sint_signal = SInt(16)[module.uint_signal]
    assert module.sint_signal.signal_type == SInt(16)


def test_uint_to_sint_invalid_truncate(module):
    module.uint_signal = Wire(UInt(8))
    with raises(ConversionNotImplemented):
        module.sint_signal = SInt(8)[module.uint_signal]


def test_invalid_sint_to_uint_generic(module):
    module.sint_signal = Wire(SInt(8))
    with raises(ConversionNotImplemented):
        module.uint_signal = UInt[module.sint_signal]


def test_invalid_sint_to_uint_sized(module):
    module.sint_signal = Wire(SInt(8))
    with raises(ConversionNotImplemented):
        module.uint_signal = UInt(16)[module.sint_signal]
