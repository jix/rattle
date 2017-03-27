from ..signal import Signal
from ..error import SignalNotTraceable


class Trace:
    def __init__(self):
        self._traces = []

    def _add_prim(self, scope, name, prim):
        # TODO handle duplicated names
        if prim.width != 0:
            self._traces.append((scope, name, prim.simplify_read()))

    def add(self, name, signal, module=None):
        if module is None:
            module = self._module_for_signal(signal)

        scope = []

        current_module = module
        while current_module is not None:
            module_name = current_module._module_data.name
            if module_name is None:
                break

            scope.append(('module', module_name))

            current_module = current_module._module_data.parent

        signal._add_to_trace(self, scope, name)

    def add_named_signals(self, module):
        for name, signal in module.__dict__.items():
            if isinstance(signal, Signal):
                try:
                    self.add(name, signal, module)
                except SignalNotTraceable:
                    pass

    @staticmethod
    def _module_for_signal(signal):
        storage_prims = set()
        for prim in signal._prims.values():
            storage_prims.update(prim.accessed_storage)

        modules = set()
        for storage_prim in storage_prims:
            modules.add(storage_prim.module)

        # TODO find parent module
        if len(modules) != 1:
            raise RuntimeError('could not determine module for traced signal')
        return next(iter(modules))
