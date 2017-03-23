from rattle.signal import *
from rattle.type import *


def test_flip_value_const(module):
    assert Bool[True].flipped.value is True
    assert UInt[42].flipped.value == 42
