from contextlib import contextmanager
from . import context
from .type.bool import Bool
from .primitive import PrimConst
from .bitvec import bv


class ConditionStack:
    def __init__(self):
        self._stack = [[]]
        # TODO Priority is only semi-related to conditions, move it elsewhere?
        self._priority_stack = [0]

    def new(self):
        self._stack[-1] = []

    def enter(self, condition, priority=None):
        if not isinstance(condition, ResetCondition):
            condition = Bool.convert(condition, implicit=True)
            condition._access()
            condition = condition._prim()
        self._stack[-1].append(condition)
        self._stack.append([])
        if priority is None:
            priority = self._priority_stack[-1]
        self._priority_stack.append(priority)

    def exit(self):
        self._stack.pop()
        self._priority_stack.pop()

    def current_conditions(self):
        conditions = []
        for level in self._stack[:-1]:
            if level:
                conditions.extend((False, neg) for neg in level[:-1])
                pos = level[-1]
                if pos != PrimConst(bv('1')):
                    conditions.append((True, pos))
        return self._priority_stack[-1], tuple(conditions)


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


class ResetCondition:
    pass

reset_condition = ResetCondition()


class ResetContext:
    def __enter__(self):
        context.current().module._module_data.condition_stack.enter(
            reset_condition, priority=1)

    def __exit__(self, *exc):
        context.current().module._module_data.condition_stack.exit()

reset = ResetContext()
