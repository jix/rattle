from rattle.circuit import Block, BlockAssign, BlockCond
from rattle.signal import *
from rattle.type import *
from rattle.conditional import *


def test_block_recover_nesting():
    block = Block()
    assignments = [
        ('S', 't0', (), 's0'),
        ('S', 't1', ((True, 'c0'),), 's1'),
        ('S', 't2', ((False, 'c0'), (True, 'c1')), 's2'),
        ('S', 't3', ((False, 'c0'), (True, 'c1'), (True, 'c2')), 's3'),
        ('S', 't4', ((False, 'c0'), (True, 'c1'), (False, 'c2')), 's4'),
        ('S', 't5', ((False, 'c0'), (False, 'c1'), (False, 'c2')), 's5'),
        ('S', 't6', ((True, 'c3'),), 's6'),
        ('S', 't7', (), 's7'),
        ('S', 't8', ((True, 'c3'),), 's8'),
        ('S', 't9', ((True, 'c4'), (True, 'c5')), 's9'),
    ]

    nested = [
        BlockAssign('S', 't0', 's0'),
        BlockCond('c0', [
            BlockAssign('S', 't1', 's1'),
        ], [
            BlockCond('c1', [
                BlockAssign('S', 't2', 's2'),
                BlockCond('c2', [
                    BlockAssign('S', 't3', 's3'),
                ], [
                    BlockAssign('S', 't4', 's4'),
                ])
            ], [
                BlockCond('c2', [], [
                    BlockAssign('S', 't5', 's5'),
                ])
            ])
        ]),
        BlockCond('c3', [
            BlockAssign('S', 't6', 's6'),
        ], []),
        BlockAssign('S', 't7', 's7'),
        BlockCond('c3', [
            BlockAssign('S', 't8', 's8'),
        ], []),
        BlockCond('c4', [
            BlockCond('c5', [
                BlockAssign('S', 't9', 's9'),
            ], [])
        ], [])
    ]

    for assignment in assignments:
        block.add_assignment(*assignment)

    assert block.assignments == nested
