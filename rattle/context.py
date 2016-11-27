import threading
from contextlib import contextmanager

from .error import NoModuleUnderConstruction

_thread_local = threading.local()


class Context:
    def __init__(self):
        self.__module = None

    @property
    def module(self):
        if self.__module is None:
            raise NoModuleUnderConstruction()
        return self.__module

    @contextmanager
    def constructing_module(self, module):
        from .conditional import ConditionStack
        old_module = self.__module
        self.__module = module
        old_condition_stack = module._module_data.condition_stack
        module._module_data.condition_stack = ConditionStack()
        try:
            yield
        finally:
            module._module_data.condition_stack = old_condition_stack
            self.__module = old_module


def current():
    try:
        return _thread_local.context
    except AttributeError:
        _thread_local.context = rv = Context()
        return rv
