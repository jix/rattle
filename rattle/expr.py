import re
from collections import namedtuple

_ops = '''
    Nop: x
    Field: name $x
    ConstIndex: index $x
    ConstSlice: start length $x
    Flip: x
    Concat: parts
    Not: x
    And Or Xor: a b
    SignExt ZeroExt: bits x
    Repeat: count x
    Bundle: fields
    Vec: elements
'''

_snake_case_re = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def _snake_case(camel_case):
    return _snake_case_re.sub(r'_\1', camel_case).lower()


for line in _ops.strip().split('\n'):
    ops, fields = line.split(':')
    ops = ops.split()
    fields = fields.split()
    field_names = [field.replace('$', '') for field in fields]
    eval_fields = [field.replace('$', '') for field in fields if '$' in field]
    if eval_fields:
        eval_field = eval_fields[0]
    else:
        eval_field = None
    for op in ops:
        op_class = namedtuple(op, field_names)
        op_class.fn_name = _snake_case(op)
        op_class.eval_fn_name = '_eval_' + _snake_case(op)
        op_class.eval_field = eval_field
        globals()[op] = op_class
