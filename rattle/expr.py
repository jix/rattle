from collections import namedtuple

Nop = namedtuple('Nop', 'expr')
Field = namedtuple('Field', 'name expr')
Flip = namedtuple('Flip', 'expr')
Concat = namedtuple('Concat', 'exprs')
Not = namedtuple('Not', 'expr')
