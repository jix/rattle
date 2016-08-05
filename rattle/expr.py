import re
from collections import namedtuple

_ops = '''
    Nop: x
    Field: name x
    Flip: x
    Concat: exprs
    Not: x
    And Or Xor: a b
    SignExt ZeroExt: bits x
    Repeat: count x
    Bundle: fields
'''

_snake_case_re = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def _snake_case(camel_case):
    return _snake_case_re.sub(r'_\1', camel_case).lower()


for line in _ops.strip().split('\n'):
    ops, fields = line.split(':')
    ops = ops.split()
    fields = fields.strip()
    for op in ops:
        op_class = namedtuple(op, fields)
        op_class.fn_name = _snake_case(op)
        op_class.eval_fn_name = '_eval_' + _snake_case(op)
        globals()[op] = op_class
