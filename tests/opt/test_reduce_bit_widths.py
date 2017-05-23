from rattle.signal import *
from rattle.type import *
from rattle.conditional import *
from rattle.primitive import *

from rattle.opt.reduce_bit_widths import ReduceBitWidths


def test_reduce_simple_not(module):
    self = module

    self.a = Reg(UInt(8), init=None)
    self.b = Reg(UInt(10), init=None)

    self.a[:] = ~self.b

    expected = PrimNot(PrimSlice(0, 8, self.b._prim()))

    circuit = self._module_data.circuit
    ReduceBitWidths(circuit)
    clocked_block = next(iter(circuit.clocked.values()))
    assert clocked_block.assignments[0].rvalue == expected.simplify_read()


def test_reduce_simple_add(module):
    self = module

    self.a = Reg(UInt(8), init=None)
    self.b = Reg(UInt(8), init=None)
    self.c = Reg(UInt(10), init=None)

    self.a[:] = self.b + self.c

    expected = PrimAdd(self.b._prim(), PrimSlice(0, 8, self.c._prim()))

    circuit = self._module_data.circuit
    ReduceBitWidths(circuit)
    clocked_block = next(iter(circuit.clocked.values()))
    assert clocked_block.assignments[0].rvalue == expected.simplify_read()


def test_reduce_simple_extend_short(module):
    self = module

    self.a = Reg(UInt(8), init=None)
    self.b = Reg(SInt(10), init=None)

    self.a[:] = self.b.extend(32)

    expected = PrimSlice(0, 8, self.b._prim())

    circuit = self._module_data.circuit
    ReduceBitWidths(circuit)
    clocked_block = next(iter(circuit.clocked.values()))
    assert clocked_block.assignments[0].rvalue == expected.simplify_read()


def test_reduce_simple_extend_wide(module):
    self = module

    self.a = Reg(UInt(10), init=None)
    self.b = Reg(SInt(8), init=None)

    self.a[:] = self.b.extend(32)

    expected = PrimSignExt(10, self.b._prim())

    circuit = self._module_data.circuit
    ReduceBitWidths(circuit)
    clocked_block = next(iter(circuit.clocked.values()))
    assert clocked_block.assignments[0].rvalue == expected.simplify_read()


def test_reduce_simple_slice(module):
    self = module

    self.a = Reg(UInt(8), init=None)
    self.b = Reg(SInt(32), init=None)

    self.a[:] = self.b[2:].as_uint()

    expected = PrimSlice(2, 8, self.b._prim())

    circuit = self._module_data.circuit
    ReduceBitWidths(circuit)
    clocked_block = next(iter(circuit.clocked.values()))
    assert clocked_block.assignments[0].rvalue == expected.simplify_read()


def test_reduce_multiple_readers_not(module):
    self = module

    self.a = Reg(UInt(8), init=None)
    self.b = Reg(UInt(10), init=None)
    self.c = Reg(UInt(32), init=None)

    self.a[:] = ~self.c
    self.b[:] = ~self.c

    expected_a = PrimSlice(0, 8, PrimNot(PrimSlice(0, 10, self.c._prim())))
    expected_b = PrimNot(PrimSlice(0, 10, self.c._prim()))

    circuit = self._module_data.circuit
    ReduceBitWidths(circuit)
    clocked_block = next(iter(circuit.clocked.values()))
    assert clocked_block.assignments[0].rvalue == expected_a.simplify_read()
    assert clocked_block.assignments[1].rvalue == expected_b.simplify_read()
