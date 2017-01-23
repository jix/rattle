from rattle.circuit import *
from rattle.signal import *
from rattle.type import *
from rattle.conditional import *


def test_block_recover_nesting():
    block = Block()
    assignments = [
        ('t0', (), 's0'),
        ('t1', ((True, 'c0'),), 's1'),
        ('t2', ((False, 'c0'), (True, 'c1')), 's2'),
        ('t3', ((False, 'c0'), (True, 'c1'), (True, 'c2')), 's3'),
        ('t4', ((False, 'c0'), (True, 'c1'), (False, 'c2')), 's4'),
        ('t5', ((False, 'c0'), (False, 'c1'), (False, 'c2')), 's5'),
        ('t6', ((True, 'c3'),), 's6'),
        ('t7', (), 's7'),
        ('t8', ((True, 'c3'),), 's8'),
        ('t9', ((True, 'c4'), (True, 'c5')), 's9'),
    ]

    nested = [
        ('=', 't0', 's0'),
        ('?', 'c0', [
            ('=', 't1', 's1'),
        ], [
            ('?', 'c1', [
                ('=', 't2', 's2'),
                ('?', 'c2', [
                    ('=', 't3', 's3'),
                ], [
                    ('=', 't4', 's4'),
                ])
            ], [
                ('?', 'c2', [], [
                    ('=', 't5', 's5'),
                ])
            ])
        ]),
        ('?', 'c3', [
            ('=', 't6', 's6'),
        ], []),
        ('=', 't7', 's7'),
        ('?', 'c3', [
            ('=', 't8', 's8'),
        ], []),
        ('?', 'c4', [
            ('?', 'c5', [
                ('=', 't9', 's9'),
            ], [])
        ], [])
    ]

    for assignment in assignments:
        block.add_assignment(*assignment)

    assert block.assignments == nested


def test_sync_reset_finalization(module):
    self = module

    self.test = Reg(Bool)

    with reset:
        self.test[:] = False

    self.test[:] = ~self.test

    self._module_data.circuit.finalize()

    assert not self._module_data.circuit.sync_reset
    clocked_block = self._module_data.circuit.clocked.popitem()[1]
    assert clocked_block.assignments[-1][0] == '?'
