import abc

from . import context
from .error import NoModuleUnderConstruction
from .conditional import ConditionStack
from .signal import Signal
from .hashutil import hash_key


class ModuleData:
    def __init__(self, ctx, module):
        self.storage_signals = []
        self.assignments = []
        self.lowered_assignments = []
        self.condition_stack = ConditionStack()
        self.implicit_bindings = {}
        self.submodules = []
        self.common_values = {}
        self.automatic_names = {}
        try:
            self.parent = ctx.module
        except NoModuleUnderConstruction:
            self.parent = None
        else:
            self.parent._module_data.submodules.append(module)


class Module(metaclass=abc.ABCMeta):
    def __init__(self, *args, **kwds):
        ctx = context.current()
        self._module_data = ModuleData(ctx, self)
        with ctx.constructing_module(self):
            self.construct(*args, **kwds)

    def __repr__(self):
        return "%s()" % type(self).__name__

    @property
    def parent(self):
        return self._module_data.parent

    @abc.abstractmethod
    def construct(self):
        pass

    def reopen(self):
        return context.current().constructing_module(self)

    def __setattr__(self, name, value):
        if isinstance(value, Signal):
            self._module_data.automatic_names[hash_key(value)] = name
        return super().__setattr__(name, value)
