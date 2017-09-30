from . import context
from .error import NoModuleUnderConstruction, SignalRedefined
from .signal import Signal
from .circuit import Circuit
from .names import Names


class ModuleMeta(type):
    def __call__(cls, *args, **kwds):
        module = cls.__new__(cls, *args, **kwds)

        ctx = context.current()
        module._module_data = ModuleData(ctx, module)
        with ctx.constructing_module(module):
            module.__init__(*args, **kwds)
        return module


class ModuleData:
    def __init__(self, ctx, module):
        self.condition_stack = None
        self.implicit_bindings = {}
        self.submodules = []
        self.io_prims = []
        self.storage_prims = []
        self.circuit = Circuit()
        self.names = Names()
        self.instance_name = None
        self.module_name = None
        self.attributes = []
        try:
            self.parent = ctx.module
        except NoModuleUnderConstruction:
            self.parent = None
        else:
            self.parent._module_data.submodules.append(module)


class Module(metaclass=ModuleMeta):
    # pylint: disable=no-member
    def __repr__(self):
        return "%s()" % type(self).__name__

    @property
    def parent(self):
        return self._module_data.parent

    def reopen(self):
        return context.current().constructing_module(self)

    def __setattr__(self, name, value):
        if isinstance(getattr(self, name, None), Signal):
            raise SignalRedefined(
                'signal %r already defined' % name)
        if isinstance(value, Signal):
            self._module_data.names.name_signal(value, name)
        elif isinstance(value, Module):
            if value.parent == self:
                self._module_data.names.name_submodule(value, name)
        return super().__setattr__(name, value)

    def trace(self, trace):
        trace.add_named_signals(self)
        for submodule in self._module_data.submodules:
            submodule.trace(trace)

    def attribute(self, *attributes):
        for attribute in attributes:
            if isinstance(attribute, type):
                attribute = attribute()
            self._module_data.attributes.append(attribute)


__all__ = ['Module']
