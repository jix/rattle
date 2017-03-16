from rattle.signal import *
from rattle.type import *
from rattle.conditional import *

from rattle.opt.find_continuous_assignments import FindContinuousAssignments


def test_find_continuous_assignments(module):
    self = module

    self.a = Latch(Bool)
    self.b = Latch(Bool)

    self.a[:] = ~self.b

    circuit = self._module_data.circuit

    FindContinuousAssignments(circuit)

    assert not circuit.combinational
    assert circuit.assign[self.a._prim()] == [
        (self.a._prim(), (~self.b)._prim())]
