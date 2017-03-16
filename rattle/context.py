import threading
from contextlib import contextmanager

from .error import NoModuleUnderConstruction

_thread_local = threading.local()


class Context:
    def __init__(self):
        self.__module = None
        self.__sim = None

    @property
    def module(self):
        if self.__module is None:
            raise NoModuleUnderConstruction()
        return self.__module

    @property
    def sim(self):
        if self.__sim is None:
            # TODO Better exception
            raise RuntimeError('no simulation active')
        return self.__sim

    @property
    def sim_active(self):
        return self.__sim is not None

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

    @contextmanager
    def activate_sim_context(self, sim):
        # TODO Also allow binding the sim context for repl use
        if self.__sim is sim:
            yield
            return
        if self.__sim is not None:
            raise RuntimeError('simulations cannot be nested')

        self.__sim = sim
        try:
            yield
        finally:
            self.__sim = None


def current():
    try:
        return _thread_local.context
    except AttributeError:
        _thread_local.context = rv = Context()
        return rv
