from collections import namedtuple

Nop = namedtuple('Nop', 'expr')
Field = namedtuple('Field', 'name expr')
Flip = namedtuple('Flip', 'expr')
Concat = namedtuple('Concat', 'exprs')
Not = namedtuple('Not', 'expr')
And = namedtuple('And', 'expr_a expr_b')
Or = namedtuple('Or', 'expr_a expr_b')
Xor = namedtuple('Xor', 'expr_a expr_b')
ZeroExt = namedtuple('ZeroExt', 'bits expr')
SignExt = namedtuple('SignExt', 'bits expr')
