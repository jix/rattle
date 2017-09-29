from pytest import raises
from rattle.type import *
from rattle.type.inout import *
from rattle.signal import *
from rattle.module import *
from rattle.verilog import Verilog
from rattle.error import UnsupportedInOutUse


def test_inout_declare_port(module):
    self = module
    self.single = InOut()
    self.wide = InOut(10)


def test_inout_invalid_declare_wire(module):
    self = module
    with raises(UnsupportedInOutUse):
        self.single = Wire(InOutType())


def test_inout_invalid_declare_reg(module):
    self = module
    with raises(UnsupportedInOutUse):
        self.single = Reg(InOutType())


def test_inout_declare_output_reg(module):
    self = module
    self.single = OutputReg(InOutType())


def test_inout_direct_connect_child_with_parent():
    class Inner(Module):
        def __init__(self):
            self.inner_port = InOut()

    class Outer(Module):
        def __init__(self):
            self.outer_port = InOut()

            self.inner = Inner()
            self.inner.inner_port[:] = self.outer_port

    outer_source = Verilog(Outer()).source
    assert '.inner_port(outer_port)' in outer_source


def test_inout_direct_connect_child_with_parent_slice():
    class Inner(Module):
        def __init__(self):
            self.inner_port = InOut(3)

    class Outer(Module):
        def __init__(self):
            self.outer_port = InOut(10)

            self.inner = Inner()
            self.inner.inner_port[:] = self.outer_port[:3]

    outer_source = Verilog(Outer()).source
    assert '.inner_port(outer_port[2:0])' in outer_source


def test_inout_direct_connect_vec_child_with_vec_parent():
    class Inner(Module):
        def __init__(self):
            self.inner_port = Output(Vec(3, Vec(2, InOutType())))

    class Outer(Module):
        def __init__(self):
            self.outer_port = Output(Vec(3, Vec(2, InOutType())))

            self.inner = Inner()
            self.inner.inner_port[:] = self.outer_port

    outer_source = Verilog(Outer()).source
    assert '.inner_port_0_0(outer_port_0_0)' in outer_source
    assert '.inner_port_0_1(outer_port_0_1)' in outer_source
    assert '.inner_port_1_0(outer_port_1_0)' in outer_source
    assert '.inner_port_1_1(outer_port_1_1)' in outer_source
    assert '.inner_port_2_0(outer_port_2_0)' in outer_source
    assert '.inner_port_2_1(outer_port_2_1)' in outer_source


def test_inout_direct_connect_children():
    class InnerA(Module):
        def __init__(self):
            self.inner_port_a = InOut()

    class InnerB(Module):
        def __init__(self):
            self.inner_port_b = InOut()

    class Outer(Module):
        def __init__(self):
            self.inner_a = InnerA()
            self.inner_b = InnerB()
            self.inner_a.inner_port_a[:] = self.inner_b.inner_port_b

    outer_source = Verilog(Outer()).source
    assert (
        '.inner_port_a(inner_b_inner_port_b)' in outer_source and
        '.inner_port_b(inner_b_inner_port_b)' in outer_source or
        '.inner_port_a(inner_a_inner_port_a)' in outer_source and
        '.inner_port_b(inner_a_inner_port_a)' in outer_source)
