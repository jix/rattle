from rattle.module import *
from rattle.signal import *
from rattle.reg import *
from rattle.type import *
from rattle.conditional import *

# TODO Currently these tests poke into internals
# replace with simulation tests when ready


def test_single_when(module):
    module.reg = Reg(Bits(10))
    module.condition = Input(Bool)
    module.reg2 = Reg(Bool)

    with when(module.condition):
        module.reg[:] = module.reg ^ Bits[0b1010101010]

    module.reg2[:] = module.condition

    assert module.reg._assignments[0][1] == ((True, module.condition),)
    assert module.reg2._assignments[0][1] == ()


def test_when_otherwise(module):
    module.reg = Reg(Bits(10))
    module.condition = Input(Bool)

    with when(module.condition):
        module.reg[:] = module.reg ^ Bits[0b1010101010]
    with otherwise:
        module.reg[:] = module.reg ^ Bits[0b1100110011]

    assert module.reg._assignments[0][1] == ((True, module.condition),)
    assert module.reg._assignments[1][1] == ((False, module.condition),)


def test_when_elwhen(module):
    module.reg = Reg(Bits(10))
    module.condition_a = Input(Bool)
    module.condition_b = Input(Bool)

    with when(module.condition_a):
        module.reg[:] = module.reg ^ Bits[0b1010101010]
    with elwhen(module.condition_b):
        module.reg[:] = module.reg ^ Bits[0b0101010101]

    assert module.reg._assignments[0][1] == (
        (True, module.condition_a),
    )
    assert module.reg._assignments[1][1] == (
        (False, module.condition_a),
        (True, module.condition_b),
    )


def test_when_elwhen_otherwise(module):
    module.reg = Reg(Bits(10))
    module.condition_a = Input(Bool)
    module.condition_b = Input(Bool)

    with when(module.condition_a):
        module.reg[:] = module.reg ^ Bits[0b1010101010]
    with elwhen(module.condition_b):
        module.reg[:] = module.reg ^ Bits[0b0101010101]
    with otherwise:
        module.reg[:] = module.reg ^ Bits[0b1100110011]

    assert module.reg._assignments[0][1] == (
        (True, module.condition_a),
    )
    assert module.reg._assignments[1][1] == (
        (False, module.condition_a),
        (True, module.condition_b),
    )
    assert module.reg._assignments[2][1] == (
        (False, module.condition_a),
        (False, module.condition_b),
    )


def test_nested_when(module):
    module.reg = Reg(Bits(10))
    module.condition_a = Input(Bool)
    module.condition_b = Input(Bool)
    module.condition_c = Input(Bool)

    with when(module.condition_a):
        with when(module.condition_b):
            module.reg[:] = module.reg ^ Bits[0b1010101010]
    with otherwise:
        with when(module.condition_b):
            module.reg[:] = module.reg ^ Bits[0b0101010101]
        with elwhen(module.condition_c):
            module.reg[:] = module.reg ^ Bits[0b1100110011]

    assert module.reg._assignments[0][1] == (
        (True, module.condition_a),
        (True, module.condition_b),
    )
    assert module.reg._assignments[1][1] == (
        (False, module.condition_a),
        (True, module.condition_b),
    )
    assert module.reg._assignments[2][1] == (
        (False, module.condition_a),
        (False, module.condition_b),
        (True, module.condition_c),
    )
