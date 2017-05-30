from pytest import raises
from rattle.signal import *
from rattle.type import *
from rattle.bitvec import bv


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


def test_bundle_packing_const():
    MyBundle = Bundle(a=Bool, b=Bits(8))
    values = {'a': True, 'b': 0b10101010}
    my_bundle = MyBundle[values]

    packed = my_bundle.packed

    unpacked = MyBundle.unpack(packed)

    assert packed.signal_type == Bits(9)
    assert packed.value == bv('101010101')
    assert unpacked.value == values


def test_bundle_packing_bidir_const():
    MyBundle = Bundle(a=Bool, b=Flip(Bits(8)), c=Flip(Bool), d=Bool)
    values = {
        'a': True,
        'b': Bits['10101010'].flipped,
        'c': Bool[False].flipped,
        'd': True
    }
    my_bundle = MyBundle[values]

    packed = my_bundle.packed

    unpacked = MyBundle.unpack(packed)

    assert packed.signal_type == Bundle(fwd=Bits(2), bwd=Flip(Bits(9)))
    assert packed.value == {'fwd': bv('11'), 'bwd': bv('010101010')}
    assert unpacked.value == my_bundle.value


def test_partial_bundle(sim_testbench):
    @sim_testbench
    def _testbench(self):
        self.wire = Wire(Bundle(a=Bool, b=UInt(8)))

        yield

        self.wire[:] = bundle(a=True, b=23)
        self.wire[:] = +bundle(a=Bool[False])

        yield

        assert self.wire.value == dict(a=False, b=23)

        self.wire[:] = -bundle(a=Bool[True], b=UInt(8)[42], c=Bool[True])

        yield

        assert self.wire.value == dict(a=True, b=42)

        with raises(KeyError):
            self.wire[:] = -bundle(a=Bool[False])

        with raises(KeyError):
            self.wire[:] = +bundle(a=Bool[True], b=UInt(8)[42], c=Bool[True])
