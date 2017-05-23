from rattle.circuit import BlockCond
from rattle.signal import *
from rattle.type import *
from rattle.conditional import *
from rattle.implicit import Implicit

from rattle.opt.lower_sync_reset import LowerSyncReset


def test_lower_sync_reset(module):
    self = module

    self.test = Reg(Bool, init=None)

    with reset:
        self.test[:] = False

    self.test[:] = ~self.test

    circuit = self._module_data.circuit

    LowerSyncReset(circuit)

    reset_prim = Implicit('clk').reset._prim()

    assert not circuit.sync_reset
    clocked_block = next(iter(circuit.clocked.values()))
    assert isinstance(clocked_block.assignments[-1], BlockCond)
    assert clocked_block.assignments[-1].condition == reset_prim
