import abc

from . import context
from . import expr
from .error import (
    InvalidSignalAccess, InvalidSignalRead, InvalidSignalAssignment)


def _check_signal_type(signal_type):
    from .type import SignalType
    if not isinstance(signal_type, SignalType):
        raise TypeError("%r is not a SignalType" % (signal_type,))
    return signal_type


class NotAccessibleClass:
    def __repr__(self):
        return "<<NotAccessible>>"

    @staticmethod
    def _allow_access_from(module):
        return False

NotAccessible = NotAccessibleClass()


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
        self.__module = module
        self.__rmodule = rmodule
        self.__lmodule = lmodule
        self.module._add_signal(self)
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
        return "%s(%r)" % (type(self).__name__, self.signal_type)

    def _access_read(self):
        module = context.current().module
        if not self.rmodule._allow_access_from(module):
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
        if not self.lmodule._allow_access_from(module):
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
        # TODO Automatic constant conversion
        value._access_read()
        # TODO Allow some automatic coercion
        if self.signal_type != value.signal_type:
            raise TypeError(
                "assignment to type %r from incompatible type %r" %
                (self.signal_type, value.signal_type))
        # TODO Conditional assignments
        # TODO Post assignment to module
        self._assignments.append(value)

    def _auto_lvalue(self, *args, **kwds):
        module = context.current().module
        allow_read = self.rmodule._allow_access_from(module)
        allow_assign = self.lmodule._allow_access_from(module)
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

        return Value(
            *args, **kwds,
            allow_read=allow_read, allow_assign=allow_assign)

    def __setitem__(self, key, value):
        self[key].assign(value)

    def __getitem__(self, key):
        if key == slice(None, None, None):
            return self
        else:
            return super().__getitem__(key)


class Wire(Signal):
    def __init__(self, signal_type):
        # TODO Allow construction with automatic assignment
        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module,
            rmodule=module)


class IOPort(Signal, metaclass=abc.ABCMeta):
    pass


class Input(IOPort):
    def __init__(self, signal_type):
        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module.parent or NotAccessible,
            rmodule=module)


class Output(IOPort):
    def __init__(self, signal_type):
        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module,
            rmodule=module.parent or NotAccessible)


class Reg(Signal):
    def __init__(self, signal_type):
        # TODO Allow construction with automatic assignment
        # TODO Allow optional enable for automatic assignment
        # TODO Allow specifying the clock
        module = context.current().module
        super().__init__(
            signal_type,
            module=module,
            lmodule=module,
            rmodule=module)


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

    @property
    def expr(self):
        return self.__expr

    def _deflip(self):
        return self

    def flip(self):
        from .type.flip import Flip
        module = context.current().module
        # Note that lmodule and rmodule are swapped below
        allow_read = self.lmodule._allow_access_from(module)
        allow_assign = self.rmodule._allow_access_from(module)
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
        return Value(
            Flip(self.signal_type), expr.Flip(self),
            allow_read=allow_read, allow_assign=allow_assign)

    @classmethod
    def _auto_concat_lvalue(cls, signals, *args, **kwds):
        module = context.current().module
        allow_read = all(
            signal.rmodule._allow_access_from(module) for signal in signals)
        allow_assign = all(
            signal.lmodule._allow_access_from(module) for signal in signals)

        if not allow_read and not allow_assign:
            # TODO More specific error messages
            raise InvalidSignalAccess(
                "concatenation of signals not accessible together "
                "from module %r" % module)

        return Value(
            *args, **kwds,
            allow_read=allow_read, allow_assign=allow_assign)


class ConstantsClass:
    @staticmethod
    def _add_signal(signal):
        pass

    @staticmethod
    def _allow_access_from(module):
        return True

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
        # TODO Let the type check/normalize the value
        self.__value = value

    @property
    def value(self):
        return self.__value

    def __repr__(self):
        return "%r[%r]" % (self.signal_type, self.value)

    def _access_read(self):
        return self
