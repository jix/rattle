from contextlib import contextmanager
from .signal import Signal, Input
from .error import ImplicitNotFound
from . import context


class ImplicitMeta(type):
    def __call__(cls, name):
        cls._check_name(name)
        module = context.current().module

        lookup_module = module
        path = []

        while True:
            path.append(lookup_module)
            try:
                value = lookup_module._module_data.implicit_bindings[name]
            except KeyError:
                lookup_module = lookup_module.parent
                if lookup_module is None:
                    raise ImplicitNotFound(
                        "implicit with name '%s' not found" % name)
            else:
                break

        if not isinstance(value, Signal):
            return value

        for (parent, child) in zip(path[::-1], path[-2::-1]):
            with child.reopen():
                implicit_input = Input(value.signal_type)
            child._module_data.implicit_bindings[name] = implicit_input
            with parent.reopen():
                implicit_input[:] = value
            value = implicit_input

        # TODO Should we ensure that this is read-only?
        return value


class Implicit(metaclass=ImplicitMeta):
    @staticmethod
    @contextmanager
    def bind(name, value, *additional_binds):
        module = context.current().module
        restores = []

        binds = ((name, value), *additional_binds)

        for bind_name, bind_value in binds:
            Implicit._check_name(bind_name)
            if isinstance(bind_value, Signal):
                bind_value._access()
            try:
                old = module._module_data.implicit_bindings[bind_name]
            except KeyError:
                restores.append((bind_name, False, None))
            else:
                restores.append((bind_name, True, old))

            module._module_data.implicit_bindings[bind_name] = bind_value

        yield

        for restore_name, present, old in restores:
            if present:
                module._module_data.implicit_bindings[restore_name] = old
            else:
                del module._module_data.implicit_bindings[restore_name]

    @staticmethod
    def _module_scope_bind(name, value):
        Implicit._check_name(name)
        module = context.current().module
        if isinstance(value, Signal):
            value._access()
        module._module_data.implicit_bindings[name] = value

    @staticmethod
    def _check_name(name):
        if not isinstance(name, str):
            raise TypeError("implicit name %r not a string", name)
        elif not all(part.isidentifier() for part in name.split('.')):
            raise ValueError(
                "implicit name '%s' is not a path of python identifiers",
                name)
