import pytest
from rattle.signal import *
from rattle.type import *


@pytest.mark.parametrize("value", [True, False])
def test_const_negate(value):
    assert (~Bool[value]).value == (not value)


@pytest.mark.parametrize("a", [True, False])
@pytest.mark.parametrize("b", [True, False])
def test_const_basic_binops(a, b):
    assert (Bool[a] & Bool[b]).value == a & b
    assert (Bool[a] ^ Bool[b]).value == a ^ b
    assert (Bool[a] | Bool[b]).value == a | b


# TODO Add simulation tests when ready

def test_construct_negate(module):
    module.input = Input(Bool)
    module.output = Output(Bool)
    module.output[:] = ~module.input


def test_construct_binops(module):
    module.a = Input(Bool)
    module.b = Input(Bool)
    module.out_and = Output(Bool)
    module.out_and[:] = module.a & module.b
    module.out_or = Output(Bool)
    module.out_or[:] = module.a | module.b
    module.out_xor = Output(Bool)
    module.out_xor[:] = module.a ^ module.b


def test_const_repeat():
    assert Bool[True].repeat(8).value == 0xFF
    assert Bool[False].repeat(8).value == 0x00
