import abc

from . import context
from . import expr
from . import hashutil
from .error import (
    InvalidSignalAccess, InvalidSignalRead, InvalidSignalAssignment,
    NoModuleUnderConstruction)


def _check_signal_type(signal_type):
    from .type import SignalType
    if not isinstance(signal_type, SignalType):
        raise TypeError("%r is not a SignalType" % (signal_type,))
    return signal_type


class NotAccessibleClass:
    def __repr__(self):
        return "<<NotAccessible>>"

NotAccessible = NotAccessibleClass()


def _allow_access(to_module, from_module):
    if to_module is NotAccessible:
        return False
    elif to_module is Constants:
        return True
    else:
        return to_module is from_module


class Signal(metaclass=abc.ABCMeta):
    def __new__(cls, *args, **kwds):
        # pylint: disable=missing-kwoa
        mixin_type, signal_type = cls._mixin_parameters(*args, **kwds)
        # TODO Memoize combined types
        # TODO If one subclass of signal_type can have instances with different
        # mixins the naming logic here fails
        combined_type = type(
            '%s(%s)' % (cls.__name__, type(signal_type).__name__),
            (mixin_type, cls), {})
        return super().__new__(combined_type)

    @classmethod
    def _mixin_parameters(cls, signal_type, *args, **kwds):
        return _check_signal_type(signal_type).signal_mixin, signal_type

    def __init__(self, signal_type, *, module, rmodule, lmodule):
        self._named = False
        self.__module = module
        self.__rmodule = rmodule
        self.__lmodule = lmodule
        self.__signal_type = signal_type
        self._assignments = []

    @property
    def signal_type(self):
        return self.__signal_type

    @property
    def module(self):
        return self.__module

    @property
    def rmodule(self):
        return self.__rmodule

    @property
    def lmodule(self):
        return self.__lmodule

    def __repr__(self):
        return "Signal(%r)" % (self.signal_type)

    def _access_read(self):
        module = context.current().module
        if not _allow_access(self.rmodule, module):
            if self.rmodule == NotAccessible:
                raise InvalidSignalRead(
                    "non-readable signal read from module %r" %
                    module)
            else:
                raise InvalidSignalRead(
                    "signal readable only from module %r read from %r" %
                    (self.rmodule, module))
        return self

    def _access_assign(self):
        module = context.current().module
        if not _allow_access(self.lmodule, module):
            if self.lmodule == NotAccessible:
                raise InvalidSignalAssignment(
                    "non-assignable signal assigned from module %r" %
                    module)
            else:
                raise InvalidSignalAssignment(
                    "signal assignable only from module %r assigned from %r" %
                    (self.lmodule, module))

    def assign(self, value):
        self._access_assign()
        value = self.signal_type.convert(value, implicit=True)
        value._access_read()
        module_data = context.current().module._module_data
        conditions = module_data.condition_stack.current_conditions()
        module_data.assignments.append((self, conditions, value))
        self._assignments.append((conditions, value))

    def _auto_lvalue(self, *args, **kwds):
        try:
            module = context.current().module
        except NoModuleUnderConstruction:
            # TODO Better error reporting for this case
            module = Constants
        allow_read = _allow_access(self.rmodule, module)
        allow_assign = _allow_access(self.lmodule, module)
        if not allow_read and not allow_assign:
            if self.rmodule == NotAccessible:
                raise InvalidSignalAccess(
                    "signal assignable only from module %r accessed from %r" %
                    (self.lmodule, module))
            elif self.lmodule == NotAccessible:
                raise InvalidSignalAccess(
                    "signal readable only from module %r accessed from %r" %
                    (self.rmodule, module))
            elif self.rmodule == self.lmodule:
                raise InvalidSignalAccess(
                    "signal accessible only from module %r accessed from %r" %
                    (self.rmodule, module))
            else:
                raise InvalidSignalAccess(
                    "signal accessible only from modules %r and %r "
                    "accessed from %r" %
                    (self.lmodule, self.rmodule, module))

        return Value._auto(
            *args, **kwds,
            allow_read=allow_read, allow_assign=allow_assign)

    def __setitem__(self, key, value):
        if key == slice(None, None, None):
            self.assign(value)

    def _convert(self, signal_type, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        return NotImplemented

    def _generic_convert(self, signal_type_class, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        return NotImplemented

    def _const_signal(self, signal_type):
        # pylint: disable=no-self-use
        return NotImplemented

    def _generic_const_signal(self, signal_type_class):
        # pylint: disable=no-self-use
        return NotImplemented

    def as_implicit(self, name):
        from .implicit import Implicit
        Implicit._module_scope_bind(name, self)
        return self

    def named(self, name=None):
        # TODO Store suggested name for the naming pass
        # TODO Check for Consts
        if not self._named:
            self._named = True
            self.module._module_data.named_signals.append(self)

    def _deflip(self):
        return self

    def flip(self):
        from .type.flip import Flip
        module = context.current().module
        # Note that lmodule and rmodule are swapped below
        allow_read = _allow_access(self.lmodule, module)
        allow_assign = _allow_access(self.rmodule, module)
        if not allow_read and not allow_assign:
            if self.rmodule == NotAccessible:
                raise InvalidSignalAccess(
                    "signal assignable only from module %r accessed from %r" %
                    (self.lmodule, module))
            elif self.lmodule == NotAccessible:
                raise InvalidSignalAccess(
                    "signal readable only from module %r accessed from %r" %
                    (self.rmodule, module))
            elif self.rmodule == self.lmodule:
                raise InvalidSignalAccess(
                    "signal accessible only from module %r accessed from %r" %
                    (self.rmodule, module))
            else:
                raise InvalidSignalAccess(
                    "signal accessible only from modules %r and %r "
                    "accessed from %r" %
                    (self.lmodule, self.rmodule, module))
        return Value._auto(
            Flip(self.signal_type), expr.Flip(self),
            allow_read=allow_read, allow_assign=allow_assign)

    def __hash__(self):
        raise TypeError("signals are not hashable")

    def _hash_key(self):
        return hashutil.HashInstance(self)


class Wire(Signal):
    def __init__(self, signal_type):
        # TODO Allow construction with automatic assignment
        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module,
            rmodule=module)
        self.named()

    def __repr__(self):
        return "Wire(%r)" % (self.signal_type)


class IOPort(Signal, metaclass=abc.ABCMeta):
    def __init__(self, signal_type, *, module, rmodule, lmodule):
        super().__init__(
            signal_type,
            module=module, rmodule=rmodule, lmodule=lmodule)
        self.named()


class Input(IOPort):
    def __init__(self, signal_type):
        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module.parent or NotAccessible,
            rmodule=module)

    def __repr__(self):
        return "Input(%r)" % (self.signal_type)


class Output(IOPort):
    def __init__(self, signal_type):
        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module,
            rmodule=module.parent or NotAccessible)

    def __repr__(self):
        return "Output(%r)" % (self.signal_type)


class Value(Signal):
    def __init__(
            self, signal_type, value_expr, *,
            allow_read=True, allow_assign=False):
        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module if allow_assign else NotAccessible,
            rmodule=module if allow_read else NotAccessible)
        self.__expr = value_expr
        self.__hash_key = (
            Value,
            allow_read,
            allow_assign,
            signal_type,
            hashutil.hash_key(value_expr))

    @property
    def expr(self):
        return self.__expr

    @staticmethod
    def _auto_concat_lvalue(signals, *args, **kwds):
        try:
            module = context.current().module
        except NoModuleUnderConstruction:
            # TODO Better error reporting for this case
            module = Constants
        allow_read = all(
            _allow_access(signal.rmodule, module) for signal in signals)
        allow_assign = all(
            _allow_access(signal.lmodule, module) for signal in signals)

        if not allow_read and not allow_assign:
            # TODO More specific error messages
            raise InvalidSignalAccess(
                "concatenation of signals not accessible together "
                "from module %r" % module)

        return Value._auto(
            *args, **kwds,
            allow_read=allow_read, allow_assign=allow_assign)

    @staticmethod
    def _auto(
            signal_type, value_expr, *,
            allow_read=True, allow_assign=False):
        if value_expr.eval_field:
            target = getattr(value_expr, value_expr.eval_field)
            fn = getattr(target.signal_type, value_expr.eval_fn_name)
            result = fn(signal_type, *value_expr)
            if result is not None:
                return result
        else:
            fn = value_expr.eval_fn_name
            try:
                fn = getattr(signal_type, fn)
            except AttributeError:
                pass
            else:
                result = fn(*value_expr)
                if result is not None:
                    return result

        module = context.current().module
        # TODO recursive computation of cache_tuple? caching of cache_tuple?

        result = Value(
            signal_type, value_expr,
            allow_read=allow_read, allow_assign=allow_assign)
        hash_key = hashutil.hash_key(result)
        try:
            return module._module_data.common_values[hash_key]
        except KeyError:
            module._module_data.common_values[hash_key] = result
            return result

    def _hash_key(self):
        return self.__hash_key


class ConstantsClass:
    pass

Constants = ConstantsClass()


class Const(Signal):
    @classmethod
    def _mixin_parameters(cls, signal_type, value):
        return _check_signal_type(signal_type).const_mixin, signal_type

    def __init__(self, signal_type, value):
        super().__init__(
            signal_type,
            module=Constants,
            lmodule=NotAccessible,
            rmodule=Constants)
        self.__value = value

    @property
    def value(self):
        return self.__value

    def __repr__(self):
        return "%r[%r]" % (self.signal_type, self.value)

    def _access_read(self):
        return self
