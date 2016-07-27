from contextlib import contextmanager
from .signal import Signal, Input
from .error import ImplicitNotFound
from . import context


class Implicit:
    def __new__(cls, name):
        cls._check_name(name)
        module = context.current().module

        lookup_module = module
        path = []

        while True:
            path.append(lookup_module)
            try:
                value = lookup_module._implicit_bindings[name]
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
            child._implicit_bindings[name] = implicit_input
            with parent.reopen():
                implicit_input[:] = value
            value = implicit_input

        # TODO Should we ensure that this is read-only?
        return value

    @staticmethod
    @contextmanager
    def bind(name, value, *additional_binds):
        module = context.current().module
        restores = []

        for name, value in ((name, value), *additional_binds):
            Implicit._check_name(name)
            if isinstance(value, Signal):
                value._access_read()
            try:
                old = module._implicit_bindings[name]
            except KeyError:
                restores.append((name, False, None))
            else:
                restores.append((name, True, old))

            module._implicit_bindings[name] = value

        yield

        for name, present, old in restores:
            if present:
                module._implicit_bindings[name] = old
            else:
                del module._implicit_bindings[name]

    @staticmethod
    def _module_scope_bind(name, value):
        Implicit._check_name(name)
        module = context.current().module
        if isinstance(value, Signal):
            value._access_read()
        module._implicit_bindings[name] = value

    @staticmethod
    def _check_name(name):
        if not isinstance(name, str):
            raise TypeError("implicit name %r not a string", name)
        elif not all(part.isidentifier() for part in name.split('.')):
            raise ValueError(
                "implicit name '%s' is not a path of python identifiers",
                name)
