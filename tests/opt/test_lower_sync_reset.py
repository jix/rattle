from rattle.circuit import *
from rattle.signal import *
from rattle.type import *
from rattle.conditional import *

from rattle.opt.lower_sync_reset import LowerSyncReset


def test_lower_sync_reset(module):
    self = module

    self.test = Reg(Bool)

    with reset:
        self.test[:] = False

    self.test[:] = ~self.test

    circuit = self._module_data.circuit

    LowerSyncReset(circuit)

    assert not circuit.sync_reset
    clocked_block = next(iter(circuit.clocked.values()))
    assert clocked_block.assignments[-1][0] == '?'
