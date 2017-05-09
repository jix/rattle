from rattle.module import Module
from rattle.signal import *
from rattle.type import *
from rattle.conditional import *


class MockCircuit:
    def __init__(self):
        self.conditions = []

    def add_combinational(self, storage, lvalue, condition, rvalue):
        self.conditions.append(condition)

    def add_clocked(self, storage, clock, lvalue, condition, rvalue):
        self.conditions.append(condition)


def test_single_when(module):
    self = module
    self._module_data.circuit = circuit = MockCircuit()
    self.reg = Reg(Bits(10))
    self.condition = Input(Bool)
    self.reg2 = Reg(Bool)

    with when(self.condition):
        self.reg[:] = self.reg ^ Bits['1010101010']

    self.reg2[:] = self.condition

    assert circuit.conditions[0] == (
        (True, self.condition._prim()),)
    assert circuit.conditions[1] == ()


def test_when_otherwise(module):
    self = module
    self._module_data.circuit = circuit = MockCircuit()
    self.reg = Reg(Bits(10))
    self.condition = Input(Bool)

    with when(self.condition):
        self.reg[:] = self.reg ^ Bits['1010101010']
    with otherwise:
        self.reg[:] = self.reg ^ Bits['1100110011']

    assert circuit.conditions[0] == (
        (True, self.condition._prim()),)
    assert circuit.conditions[1] == (
        (False, self.condition._prim()),)


def test_when_elwhen(module):
    self = module
    self._module_data.circuit = circuit = MockCircuit()
    self.reg = Reg(Bits(10))
    self.condition_a = Input(Bool)
    self.condition_b = Input(Bool)

    with when(self.condition_a):
        self.reg[:] = self.reg ^ Bits['1010101010']
    with elwhen(self.condition_b):
        self.reg[:] = self.reg ^ Bits['0101010101']

    assert circuit.conditions[0] == (
        (True, self.condition_a._prim()),
    )
    assert circuit.conditions[1] == (
        (False, self.condition_a._prim()),
        (True, self.condition_b._prim()),
    )


def test_when_elwhen_otherwise(module):
    self = module
    self._module_data.circuit = circuit = MockCircuit()
    self.reg = Reg(Bits(10))
    self.condition_a = Input(Bool)
    self.condition_b = Input(Bool)

    with when(self.condition_a):
        self.reg[:] = self.reg ^ Bits['1010101010']
    with elwhen(self.condition_b):
        self.reg[:] = self.reg ^ Bits['0101010101']
    with otherwise:
        self.reg[:] = self.reg ^ Bits['1100110011']

    assert circuit.conditions[0] == (
        (True, self.condition_a._prim()),
    )
    assert circuit.conditions[1] == (
        (False, self.condition_a._prim()),
        (True, self.condition_b._prim()),
    )
    assert circuit.conditions[2] == (
        (False, self.condition_a._prim()),
        (False, self.condition_b._prim()),
    )


def test_nested_when(module):
    self = module
    self._module_data.circuit = circuit = MockCircuit()
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

    assert circuit.conditions[0] == (
        (True, self.condition_a._prim()),
        (True, self.condition_b._prim()),
    )
    assert circuit.conditions[1] == (
        (False, self.condition_a._prim()),
        (True, self.condition_b._prim()),
    )
    assert circuit.conditions[2] == (
        (False, self.condition_a._prim()),
        (False, self.condition_b._prim()),
        (True, self.condition_c._prim()),
    )


def test_implicit_reopening(module):
    self = module
    self._module_data.circuit = circuit = MockCircuit()

    class SubModule(Module):
        def __init__(self):
            self.output = Output(UInt(8))
            self.reg = Reg(UInt(8))

            self.reg[:] = self.reg + 1

    self.en = Input(Bool)
    self.output = OutputLatch(UInt(8))

    with when(self.en):
        # The following line generates an implicit clock connection
        self.counter = SubModule()
        self.output[:] = self.counter.output
    with otherwise:
        self.output[:] = 0

    assert circuit.conditions[0] == ()  # clk X
    assert circuit.conditions[1] == ()  # clk implicit
    assert circuit.conditions[2] == ()  # reset X
    assert circuit.conditions[3] == ()  # reset implicit

    assert circuit.conditions[4] == (
        (True, self.en._prim()),
    )
    assert circuit.conditions[5] == (
        (False, self.en._prim()),
    )
