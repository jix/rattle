from pytest import raises
from rattle.module import *
from rattle.signal import *
from rattle.type import *
from rattle.error import *
from rattle.implicit import *


def test_simple_implicit():
    class Outer(Module):
        def construct(self):
            self.input = Input(Bool)
            self.output = Output(Bool)

            with Implicit.bind('implicit', self.input):
                self.inner = Inner()

            self.output[:] = self.inner.output

    class Inner(Module):
        def construct(self):
            self.output = Output(Bool)
            self.output[:] = Implicit('implicit')

    Outer()


def test_missing_implicit(module):
    with raises(ImplicitNotFound):
        Implicit('missing')


def test_bind_invalid_name(module):
    self = module
    self.input = Input(Bool)
    with raises(ValueError):
        with Implicit.bind('invalid..path', self.input):
            pass
    with raises(ValueError):
        with Implicit.bind('42', self.input):
            pass
    with raises(TypeError):
        with Implicit.bind(42, self.input):
            pass


def test_lookup_invalid_name(module):
    with raises(ValueError):
        Implicit('invalid..path')
    with raises(ValueError):
        Implicit('42')
    with raises(TypeError):
        Implicit(42)


def test_shadowing_implicit():
    class Outer(Module):
        def construct(self):
            self.input = Input(Bool)

            with Implicit.bind('implicit', self.input):
                self.middle = Middle()

    class Middle(Module):
        def construct(self):
            self.reg_bits = Reg(Bits(10))
            self.reg_bool = Reg(Bool)

            self.reg_bool[:] = Implicit('implicit')

            self.inner_bool_a = Inner(Bool)

            with Implicit.bind('implicit', self.reg_bits):
                self.inner_bits = Inner(Bits(10))

            self.inner_bool_b = Inner(Bool)

    class Inner(Module):
        def construct(self, expected_type):
            assert Implicit('implicit').signal_type == expected_type

    Outer()


def test_non_signal_implicit():
    class Outer(Module):
        def construct(self):
            with Implicit.bind('implicit', 23):
                self.inner = Inner()

    class Inner(Module):
        def construct(self):
            assert Implicit('implicit') == 23

    Outer()


def test_paths_as_names():
    class Outer(Module):
        def construct(self):
            with Implicit.bind('implicit.path', 23):
                self.inner = Inner()

    class Inner(Module):
        def construct(self):
            assert Implicit('implicit.path') == 23

    Outer()


def test_non_readable_signal(module):
    self = module
    self.output = Output(Bool)
    with raises(InvalidSignalRead):
        with Implicit.bind('implicit', self.output):
            pass


def test_module_scope_binds():
    class Outer(Module):
        def construct(self):
            self.input = Input(Bool).as_implicit('implicit')
            self.inner = Inner()

    class Inner(Module):
        def construct(self):
            assert Implicit('implicit').signal_type == Bool

    Outer()
