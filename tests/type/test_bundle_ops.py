from pytest import raises
from rattle.module import *
from rattle.signal import *
from rattle.type import *


def test_bundle_field_access(module):
    self = module
    self.bundle = Wire(Bundle(a=Bool, b=Bits(8)))
    self.bool = Wire(Bool)
    self.bits = Wire(Bits(8))
    assert self.bundle['a'].signal_type == Bool
    self.bundle['a'][:] = self.bool
    assert self.bundle.b.signal_type == Bits(8)
    self.bundle.b[:] = self.bits


def test_bundle_construction(module):
    self = module
    MyBundle = Bundle(a=Bool, b=Bits(8))
    self.bool = Wire(Bool)
    self.bits = Wire(Bits(8))

    self.bundle_1 = MyBundle[{'a': self.bool, 'b': self.bits}]
    self.bundle_2 = MyBundle[{'a': True, 'b': 0b10101010}]

    self.bundle_1[:] = self.bundle_2


def test_bundle_construction_invalid_missing(module):
    self = module
    MyBundle = Bundle(a=Bool, b=Bits(8))
    self.bool = Wire(Bool)
    self.bits = Wire(Bits(8))
    with raises(KeyError):
        self.bundle = MyBundle[{'a': self.bool}]


def test_bundle_construction_invalid_extra(module):
    self = module
    MyBundle = Bundle(a=Bool, b=Bits(8))
    self.bool = Wire(Bool)
    self.bits = Wire(Bits(8))
    with raises(KeyError):
        self.bundle = MyBundle[{
            'a': self.bool, 'b': self.bits, 'c': self.bits}]


def test_bundle_construction_const():
    MyBundle = Bundle(a=Bool, b=Bits(8))
    values = {'a': True, 'b': 0b10101010}
    assert MyBundle[values].value == values


def test_bundle_field_access_const():
    MyBundle = Bundle(a=Bool, b=Bits(8))
    values = {'a': True, 'b': 0b10101010}
    my_bundle = MyBundle[values]
    assert my_bundle.a.value
    assert my_bundle.b.value == 0b10101010


def test_bundle_construction_helper_fn_non_const(module):
    self = module
    MyBundle = Bundle(a=Bool, b=Bits(8))
    self.bool = Wire(Bool)
    self.bits = Wire(Bits(8))
    self.bundle = bundle(a=self.bool, b=self.bits)
    assert self.bundle.signal_type == MyBundle


def test_bundle_construction_helper_fn_const(module):
    self = module
    self.bundle = Wire(Bundle(a=Bool, b=Bits(8)))
    self.bits = Wire(Bits(8))
    self.bundle[:] = bundle(a=True, b=self.bits)
