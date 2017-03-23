from rattle.signal import *
from rattle.type import *
from rattle.bitvec import bv


def test_packed_bundle_const():
    MyBundle = Bundle(a=Bool, b=Bits(8))
    values = {'a': True, 'b': 0b10101010}
    my_bundle = Packed(MyBundle)[values]

    assert my_bundle.packed.signal_type == Bits(9)
    assert my_bundle.packed.value == bv('101010101')
    assert my_bundle.unpacked.value == values
    assert my_bundle.value == values


def test_packed_vec_const():
    MyVec = Vec(2, Vec(3, Bits(4)))

    values = (
        (bv('0000'), bv('1111'), bv('0101')),
        (bv('1100'), bv('1010'), bv('1110'))
    )

    my_vec = Packed(MyVec)[values]

    assert my_vec.packed.signal_type == Bits(2 * 3 * 4)
    assert my_vec.packed.value == bv('111010101100010111110000')
    assert my_vec.unpacked.value == values
    assert my_vec.value == values
