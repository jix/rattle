from collections import namedtuple

Field = namedtuple('Field', 'name expr')
Flip = namedtuple('Flip', 'expr')
Concat = namedtuple('Concat', 'exprs')
