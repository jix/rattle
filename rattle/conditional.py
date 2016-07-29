from contextlib import contextmanager
from . import context
from .signal import Const
from .type.bool import Bool


class ConditionStack:
    def __init__(self):
        self._stack = [[]]

    def new(self):
        self._stack[-1] = []

    def enter(self, condition):
        condition = Bool.convert(condition, implicit=True)
        self._stack[-1].append(condition)
        self._stack.append([])

    def exit(self):
        self._stack.pop()

    def current_conditions(self):
        conditions = []
        for level in self._stack:
            if level:
                conditions.extend((False, neg) for neg in level[:-1])
                pos = level[-1]
                if not (isinstance(pos, Const) and pos.value):
                    conditions.append((True, level[-1]))
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
