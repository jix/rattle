from hypothesis import given
import hypothesis.strategies as st
from rattle.module import *
from rattle.signal import *
from rattle.type import *


@st.composite
def const_bits_pair(draw):
    width = draw(st.integers(0, 65))
    bits_type = Bits(width)
    value_a = draw(st.integers(0, (1 << width) - 1))
    value_b = draw(st.integers(0, (1 << width) - 1))
    return bits_type[value_a], bits_type[value_b]


def test_const_negate():
    assert (~Bits(12)[1337]).value == 2758


def test_const_binops():
    assert (Bits(4)[12] & Bits(4)[10]).value == 8
    assert (Bits(4)[12] | Bits(4)[10]).value == 14
    assert (Bits(4)[12] ^ Bits(4)[10]).value == 6


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


def test_bits_dynamic_indexing(module):
    self = module
    self.index = Wire(Bits(4))
    self.bits = Wire(Bits(16))
    self.result = self.bits[self.index]

    assert self.result.signal_type == Bool


def test_bits_dynamic_indexing_const():
    v = Bits(7)['0001x10']

    assert v[Bits(3)['000']].value is False
    assert v[Bits(3)['00x']].value is X
    assert v[Bits(3)['0x1']].value is True
    assert v[Bits(3)['01x']].value is X
    assert v[Bits(3)['111']].value is X
    assert v[Bits(3)['1xx']].value is X


def test_bits_eq(module):
    self = module
    self.a = Wire(Bits(8))
    self.b = Wire(Bits(8))

    assert (self.a == self.b).signal_type == Bool


@given(const_bits_pair())  # pylint: disable=no-value-for-parameter
def test_bits_eq_const(bits_pair):
    a, b = bits_pair
    assert (a == b).value == (a.value == b.value)
    assert (a == a).value is True
