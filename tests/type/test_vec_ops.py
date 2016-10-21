from pytest import raises
from rattle.module import *
from rattle.signal import *
from rattle.type import *


def test_vec_const_indexing(module):
    self = module
    self.vec = Wire(Vec(4, Bits(8)))
    self.bits_a = Wire(Bits(8))
    self.bits_b = Wire(Bits(8))
    assert self.vec[0].signal_type == Bits(8)
    self.vec[1][:] = self.bits_a
    assert self.vec[-1].signal_type == Bits(8)
    self.vec[-2][:] = self.bits_b


def test_vec_const_invalid_indexing(module):
    self = module
    self.vec = Wire(Vec(4, Bits(8)))
    self.bits_a = Wire(Bits(8))
    self.bits_b = Wire(Bits(8))
    with raises(IndexError):
        self.vec[4][:] = self.bits_a
    with raises(IndexError):
        self.bits_b[:] = self.vec[-5]


def test_vec_construction(module):
    self = module
    self.a, self.b, self.c, self.d = (Wire(Bool) for i in range(4))

    self.vec_1 = Vec(4, Bool)[self.a, self.b, self.c, self.d]
    self.vec_2 = Vec(4, Bool)[True, False, True, False]

    self.vec_1[:] = self.vec_2


def test_vec_construction_const():
    MyVec = Vec(4, Bool)
    values = (True, False, True, False)
    assert MyVec[values].value == values


def test_vec_field_access_const():
    MyVec = Vec(4, Bits(8))
    values = [1, 2, 3, 4]
    my_vec = MyVec[values]
    assert my_vec[0].value == 1
    assert my_vec[-1].value == 4


def test_vec_construction_helper_fn_non_const(module):
    self = module
    MyVec = Vec(2, Bits(8))
    self.bits_a = Wire(Bits(8))
    self.bits_b = Wire(Bits(8))
    self.vec = vec(self.bits_a, self.bits_b)
    assert self.vec.signal_type == MyVec


def test_vec_construction_helper_fn_const(module):
    self = module
    self.vec = Wire(Vec(2, Bits(8)))
    self.bits = Wire(Bits(8))
    self.vec[:] = vec(5, self.bits)


def test_vec_const_slicing(module):
    self = module
    self.vec1 = Wire(Vec(4, Bits(8)))
    self.vec2 = Wire(Vec(8, Bits(8)))
    assert self.vec1[0:2].signal_type == Vec(2, Bits(8))
    self.vec1[0:2][:] = self.vec2[2:4]
    assert self.vec1[-3:].signal_type == Vec(3, Bits(8))
    self.vec1[-3:][:] = self.vec2[5:]
    assert self.vec1[1:[2]].signal_type == Vec(2, Bits(8))
    self.vec1[1:[2]][:] = self.vec2[5:[2]]


def test_vec_slice_access_const():
    MyVec = Vec(8, Bits(8))
    values = [1, 2, 3, 4, 5, 6, 7, 8]
    my_vec = MyVec[values]
    assert my_vec[0:3].value == (1, 2, 3)
    assert my_vec[4:].value == (5, 6, 7, 8)
    assert my_vec[:4].value == (1, 2, 3, 4)
    assert my_vec[2:[4]].value == (3, 4, 5, 6)