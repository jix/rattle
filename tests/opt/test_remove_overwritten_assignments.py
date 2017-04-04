from rattle.signal import *
from rattle.type import *
from rattle.conditional import *
from rattle.circuit import BlockAssign, BlockCond
from rattle.primitive import PrimConst, PrimSlice
from rattle.bitvec import bv

from rattle.opt.remove_overwritten_assignments import (
    RemoveOverwrittenAssignments)


def test_remove_overwritten_assignments(module):
    self = module

    self.a = Latch(Bool)
    self.b = Latch(Bool)
    self.c = Latch(Bool)

    self.d = Latch(Bits(3))

    self.a[:] = True
    self.a[:] = False

    self.b[:] = True

    with when(self.a):
        self.b[:] = self.c
        self.c[:] = True
    with otherwise:
        self.b[:] = False
        self.c[:] = self.b

    self.c[:] = False

    self.d[:] = '010'
    self.d[1][:] = 0

    circuit = self._module_data.circuit

    RemoveOverwrittenAssignments(circuit)

    assert circuit.combinational[self.a._prim()].assignments == [
        BlockAssign(self.a._prim(), self.a._prim(), PrimConst(bv('0')))
    ]

    assert circuit.combinational[self.b._prim()].assignments == [
        BlockCond(
            self.a._prim(),
            [BlockAssign(self.b._prim(), self.b._prim(), self.c._prim())],
            [BlockAssign(self.b._prim(), self.b._prim(), PrimConst(bv('0')))],
        )
    ]

    assert circuit.combinational[self.c._prim()].assignments == [
        BlockAssign(self.c._prim(), self.c._prim(), PrimConst(bv('0')))
    ]

    assert circuit.combinational[self.d._prim()].assignments == [
        BlockAssign(self.d._prim(), self.d._prim(), PrimConst(bv('010'))),
        BlockAssign(
            self.d._prim(),
            PrimSlice(1, 1, self.d._prim()),
            PrimConst(bv('0'))),
    ]
