import abc

from . import context
from .error import NoModuleUnderConstruction
from .conditional import ConditionStack


class Module(metaclass=abc.ABCMeta):
    def __init__(self, *args, **kwds):
        ctx = context.current()
        self.__signals = []
        self.__assignments = []
        self._condition_stack = ConditionStack()
        self._implicit_bindings = {}
        try:
            self.__parent = ctx.module
        except NoModuleUnderConstruction:
            self.__parent = None
        with ctx.constructing_module(self):
            self.construct(*args, **kwds)

    def __repr__(self):
        return "%s()" % type(self).__name__

    @property
    def parent(self):
        return self.__parent

    def _add_signal(self, signal):
        self.__signals.append(signal)

    def _add_assignment(self, target, condition, value):
        self.__assignments.append((target, condition, value))

    def _allow_access_from(self, module):
        return self == module

    @abc.abstractmethod
    def construct(self):
        pass

    def reopen(self):
        return context.current().constructing_module(self)
