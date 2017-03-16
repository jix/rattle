from contextlib import contextmanager
from . import context
from .type.bool import Bool
from .primitive import PrimConst
from .bitvec import bv


class ConditionStack:
    def __init__(self):
        self._stack = [[]]

    def new(self):
        self._stack[-1] = []

    def enter(self, condition):
        if self.is_reset():
            raise RuntimeError(
                'conditions cannot be used inside a reset block')
        condition = Bool.convert(condition, implicit=True)
        condition._access()
        condition = condition._prim().simplify_read()
        self._stack[-1].append(condition)
        self._stack.append([])

    def enter_reset(self):
        if len(self._stack) > 1:
            # TODO Specific exception
            raise RuntimeError('reset cannot be nested in conditions')
        self._stack.append('reset')

    def is_reset(self):
        return self._stack[-1] == 'reset'

    def exit(self):
        self._stack.pop()

    def current_conditions(self):
        if self.is_reset():
            return ()
        conditions = []
        for level in self._stack[:-1]:
            if level:
                conditions.extend((False, neg) for neg in level[:-1])
                pos = level[-1]
                if pos != PrimConst(bv('1')):
                    conditions.append((True, pos))
        return tuple(conditions)


@contextmanager
def when(condition):
    stack = context.current().module._module_data.condition_stack
    stack.new()
    stack.enter(condition)
    yield
    stack.exit()


@contextmanager
def elwhen(condition):
    stack = context.current().module._module_data.condition_stack
    stack.enter(condition)
    yield
    stack.exit()


class OtherwiseContext:
    def __enter__(self):
        context.current().module._module_data.condition_stack.enter(Bool[True])

    def __exit__(self, *exc):
        context.current().module._module_data.condition_stack.exit()


otherwise = OtherwiseContext()


class ResetContext:
    def __enter__(self):
        context.current().module._module_data.condition_stack.enter_reset()

    def __exit__(self, *exc):
        context.current().module._module_data.condition_stack.exit()


reset = ResetContext()


__all__ = [
    'when',
    'elwhen',
    'otherwise',
    'reset',
]
