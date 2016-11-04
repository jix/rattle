import builtins
from hypothesis import given
import hypothesis.strategies as st
from rattle.module import *
from rattle.signal import *
from rattle.type import *


@st.composite
def const_ints(draw):
    signed = draw(st.booleans())
    min_width = builtins.int(signed)
    width = draw(st.integers(min_width, 65))
    int_type = SInt(width) if signed else UInt(width)
    value = draw(st.integers(int_type.min_value, int_type.max_value))
    return int_type[value]


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


def test_add_coercion(module):
    self = module
    self.uint4 = Wire(UInt(4))
    self.sint4 = Wire(SInt(4))
    self.uint8 = Wire(UInt(8))
    self.sint8 = Wire(SInt(8))

    assert (self.uint4 + self.uint4).signal_type == UInt(5)
    assert (self.uint4 + self.sint4).signal_type == SInt(6)
    assert (self.uint4 + self.uint8).signal_type == UInt(9)
    assert (self.uint4 + self.sint8).signal_type == SInt(9)
    assert (self.sint4 + self.sint4).signal_type == SInt(5)
    assert (self.sint4 + self.uint8).signal_type == SInt(10)
    assert (self.sint4 + self.sint8).signal_type == SInt(9)


@given(const_ints(), const_ints())  # pylint: disable=no-value-for-parameter
def test_add_const(a, b):
    assert (a + b).value == a.value + b.value


@given(const_ints(), st.integers())  # pylint: disable=no-value-for-parameter
def test_add_const_coerce_py_int(a, b):
    assert (a + b).value == a.value + b
    assert (b + a).value == b + a.value


@given(const_ints(), const_ints())  # pylint: disable=no-value-for-parameter
def test_sub_const(a, b):
    assert (a - b).value == a.value - b.value


@given(const_ints(), st.integers())  # pylint: disable=no-value-for-parameter
def test_sub_const_coerce_py_int(a, b):
    assert (a - b).value == a.value - b
    assert (b - a).value == b - a.value


@given(const_ints(), const_ints())  # pylint: disable=no-value-for-parameter
def test_mul_const(a, b):
    assert (a * b).value == a.value * b.value


@given(const_ints(), st.integers())  # pylint: disable=no-value-for-parameter
def test_mul_const_coerce_py_int(a, b):
    assert (a * b).value == a.value * b
    assert (b * a).value == b * a.value


@given(const_ints())  # pylint: disable=no-value-for-parameter
def test_neg_const(a):
    assert (-a).value == -(a.value)


def test_eq(module):
    self = module
    self.uint4 = Wire(UInt(4))
    self.sint4 = Wire(SInt(4))
    self.uint8 = Wire(UInt(8))
    self.sint8 = Wire(SInt(8))

    assert (self.uint4 == self.uint4).signal_type == Bool
    assert (self.uint4 == self.sint4).signal_type == Bool
    assert (self.uint4 == self.uint8).signal_type == Bool
    assert (self.uint4 == self.sint8).signal_type == Bool
    assert (self.sint4 == self.sint4).signal_type == Bool
    assert (self.sint4 == self.uint8).signal_type == Bool
    assert (self.sint4 == self.sint8).signal_type == Bool


@given(const_ints(), const_ints())  # pylint: disable=no-value-for-parameter
def test_eq_const(a, b):
    assert (a == b).value == (a.value == b.value)
