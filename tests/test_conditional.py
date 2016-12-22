from rattle.module import *
from rattle.signal import *
from rattle.type import *
from rattle.conditional import *


def test_single_when(module):
    self = module
    self.reg = Reg(Bits(10))
    self.condition = Input(Bool)
    self.reg2 = Reg(Bool)

    with when(self.condition):
        self.reg[:] = self.reg ^ Bits['1010101010']

    self.reg2[:] = self.condition

    assert self._module_data.assignments[0][2] == (
        (True, self.condition._prim()),)
    assert self._module_data.assignments[1][2] == ()


def test_when_otherwise(module):
    self = module
    self.reg = Reg(Bits(10))
    self.condition = Input(Bool)

    with when(self.condition):
        self.reg[:] = self.reg ^ Bits['1010101010']
    with otherwise:
        self.reg[:] = self.reg ^ Bits['1100110011']

    assert self._module_data.assignments[0][2] == (
        (True, self.condition._prim()),)
    assert self._module_data.assignments[1][2] == (
        (False, self.condition._prim()),)


def test_when_elwhen(module):
    self = module
    self.reg = Reg(Bits(10))
    self.condition_a = Input(Bool)
    self.condition_b = Input(Bool)

    with when(self.condition_a):
        self.reg[:] = self.reg ^ Bits['1010101010']
    with elwhen(self.condition_b):
        self.reg[:] = self.reg ^ Bits['0101010101']

    assert self._module_data.assignments[0][2] == (
        (True, self.condition_a._prim()),
    )
    assert self._module_data.assignments[1][2] == (
        (False, self.condition_a._prim()),
        (True, self.condition_b._prim()),
    )


def test_when_elwhen_otherwise(module):
    self = module
    self.reg = Reg(Bits(10))
    self.condition_a = Input(Bool)
    self.condition_b = Input(Bool)

    with when(self.condition_a):
        self.reg[:] = self.reg ^ Bits['1010101010']
    with elwhen(self.condition_b):
        self.reg[:] = self.reg ^ Bits['0101010101']
    with otherwise:
        self.reg[:] = self.reg ^ Bits['1100110011']

    assert self._module_data.assignments[0][2] == (
        (True, self.condition_a._prim()),
    )
    assert self._module_data.assignments[1][2] == (
        (False, self.condition_a._prim()),
        (True, self.condition_b._prim()),
    )
    assert self._module_data.assignments[2][2] == (
        (False, self.condition_a._prim()),
        (False, self.condition_b._prim()),
    )


def test_nested_when(module):
    self = module
    self.reg = Reg(Bits(10))
    self.condition_a = Input(Bool)
    self.condition_b = Input(Bool)
    self.condition_c = Input(Bool)

    with when(self.condition_a):
        with when(self.condition_b):
            self.reg[:] = self.reg ^ Bits['1010101010']
    with otherwise:
        with when(self.condition_b):
            self.reg[:] = self.reg ^ Bits['0101010101']
        with elwhen(self.condition_c):
            self.reg[:] = self.reg ^ Bits['1100110011']

    assert self._module_data.assignments[0][2] == (
        (True, self.condition_a._prim()),
        (True, self.condition_b._prim()),
    )
    assert self._module_data.assignments[1][2] == (
        (False, self.condition_a._prim()),
        (True, self.condition_b._prim()),
    )
    assert self._module_data.assignments[2][2] == (
        (False, self.condition_a._prim()),
        (False, self.condition_b._prim()),
        (True, self.condition_c._prim()),
    )


def test_implicit_reopening(module):
    self = module

    class SubModule(Module):
        def construct(self):
            self.output = Output(UInt(8))
            self.reg = Reg(UInt(8))

            self.reg[:] = self.reg + 1

    self.en = Input(Bool)
    self.output = Output(UInt(8))

    with when(self.en):
        # The following line generates an implicit clock connection
        self.counter = SubModule()
        self.output[:] = self.counter.output
    with otherwise:
        self.output[:] = 0

    assert self._module_data.assignments[0][2] == ()  # clk
    assert self._module_data.assignments[1][2] == ()  # reset
    assert self._module_data.assignments[2][2] == (
        (True, self.en._prim()),
    )
    assert self._module_data.assignments[3][2] == (
        (False, self.en._prim()),
    )
