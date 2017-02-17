from collections import OrderedDict
from ..circuit import Block


class LowerSyncReset:
    def __init__(self, circuit):
        for clock, reset_block in circuit.sync_reset.items():
            try:
                block = circuit.clocked[clock]
            except KeyError:
                block = circuit.clocked[clock] = Block()
            block.assignments.extend(reset_block.assignments)
            block.storage.update(reset_block.storage)

        circuit.sync_reset = OrderedDict()
