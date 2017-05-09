from pytest import raises
from rattle.signal import *
from rattle.module import Module
from rattle.type import *
from rattle.error import InvalidSignalRead, InvalidSignalAssignment


def test_wire_invalid_read():
    class Mod1(Module):
        def __init__(self):
            self.wire = Wire(Bool)

    class Mod2(Module):
        def __init__(self):
            self.mod1 = Mod1()
            self.wire = Wire(Bool)
            with raises(InvalidSignalRead):
                self.wire[:] = self.mod1.wire
    Mod2()


def test_wire_invalid_assignment():
    class Mod1(Module):
        def __init__(self):
            self.wire = Wire(Bool)

    class Mod2(Module):
        def __init__(self):
            self.mod1 = Mod1()
            self.wire = Wire(Bool)
            with raises(InvalidSignalAssignment):
                self.mod1.wire[:] = self.wire
    Mod2()


def test_input_outside_read():
    class Mod1(Module):
        def __init__(self):
            self.input = Input(Bool)

    class Mod2(Module):
        def __init__(self):
            self.mod1 = Mod1()
            self.wire = Wire(Bool)
            self.wire[:] = self.mod1.input
    Mod2()


def test_input_invalid_assignment():
    class Mod(Module):
        def __init__(self):
            self.input = Input(Bool)
            with raises(InvalidSignalAssignment):
                self.input[:] = self.input
    Mod()


def test_output_inside_read():
    class Mod(Module):
        def __init__(self):
            self.output = Output(Bool)
            self.wire = Wire(Bool)
            self.wire[:] = self.output
    Mod()


def test_output_invalid_assignment():
    class Mod1(Module):
        def __init__(self):
            self.output = Output(Bool)

    class Mod2(Module):
        def __init__(self):
            self.mod1 = Mod1()
            self.wire = Wire(Bool)
            with raises(InvalidSignalAssignment):
                self.mod1.output[:] = self.wire
    Mod2()


def test_constant_invalid_assignment(module):
    with raises(InvalidSignalAssignment):
        Bool[True][:] = Bool[False]

# TODO tests with flip
