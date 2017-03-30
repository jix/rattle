import pytest
from rattle.prelude import *


def test_enum_declaration_implicit_state_encoding():
    E = Enum('A', 'B', 'C')

    assert E == Enum(
        ('A', '00'),
        ('B', '01'),
        ('C', '10'),
    )


def test_enum_declaration_implicit_state_and_data_encoding():
    E = Enum(
        ('A', dict(x=Bits(2), y=Bool)),
        ('B', dict(z=Vec(3, Bits(2)))),
        ('C')
    )

    assert E == Enum(
        ('A', '00', dict(x=Bits(2), y=Bool)),
        ('B', '01', dict(z=Vec(3, Bits(2)))),
        ('C', '10'),
    )

    assert E == Enum(
        ('A', None, '000{y}{x}', dict(x=Bits(2), y=Bool)),
        ('B', None, '{z}', dict(z=Vec(3, Bits(2)))),
        ('C', None, '000000'),
    )

    assert E == Enum(
        ('A', '00', '000{y}{x}', dict(x=Bits(2), y=Bool)),
        ('B', '01', '{z}', dict(z=Vec(3, Bits(2)))),
        ('C', '10', '000000'),
    )


def test_enum_declaration_implicit_data_encoding():
    E = Enum(
        ('A', '1--', dict(x=Bits(2), y=Bool)),
        ('B', '01-', dict(z=Vec(3, Bits(2)))),
        ('C', '001')
    )

    assert E == Enum(
        ('A', '1--', '000{y}{x}', dict(x=Bits(2), y=Bool)),
        ('B', '01-', '{z}', dict(z=Vec(3, Bits(2)))),
        ('C', '001', '000000'),
    )


def test_basic_enum(sim_testbench):
    E = Enum('A', 'B', 'C')

    @sim_testbench
    def _testbench(self):
        self.x = Reg(E)
        self.y = Reg(E)

        self.x_is_C = Wire(Bool)

        self.x_is_C[:] = False
        with self.x.C:
            self.x_is_C[:] = True

        yield

        self.x[:] = 'A'
        self.y[:] = 'B'

        yield self.clk

        assert not self.x_is_C.value
        assert (self.x == 'A').value
        assert (self.y == 'B').value

        self.x[:] = E.B
        self.y[:] = E.C

        yield self.clk

        assert not self.x_is_C.value
        assert (self.x == E.B).value
        assert (self.y == E.C).value

        self.x[:] = self.y
        self.y[:] = self.x

        yield self.clk

        assert self.x_is_C.value
        assert (self.y == E.B()).value

        assert self.x.valid_state.value
        assert self.y.valid_state.value

        self.x[:] = E.unpack('11')

        yield self.clk

        assert not self.x.valid_state.value


def test_dont_care_encoding(sim_testbench):
    E = Enum(
        ('A', '1-x'),
        ('B', '01+'),
        ('C', '001'),
    )

    for v in ('100', '111', '101'):
        assert Bool[E.unpack(v).A].value is True
        assert Bool[E.unpack(v).B].value is False
        assert Bool[E.unpack(v).C].value is False

    for v in ('010', '011'):
        assert Bool[E.unpack(v).A].value is False
        assert Bool[E.unpack(v).B].value is True
        assert Bool[E.unpack(v).C].value is False

    assert Bool[E.unpack('001').A].value is False
    assert Bool[E.unpack('001').B].value is False
    assert Bool[E.unpack('001').C].value is True

    assert E.A().packed.value.same_as(bv('10x'))
    assert E.B().packed.value.same_as(bv('011'))
    assert E.C().packed.value.same_as(bv('001'))


E1 = Enum(
    ('A', dict(x=Bool, y=Bool)),
    ('B', dict(z=UInt(4))),
    'C',
)

E2 = Enum(
    ('A', '1 0-{y}{x}', dict(x=Bool, y=Bool)),
    ('B', '0 {     z}', dict(z=UInt(4))),
    ('C', '1 1    +++'),
)


@pytest.mark.parametrize('enum_type', [E1, E2])
def test_enum_data(enum_type, sim_testbench):
    E = enum_type

    @sim_testbench
    def _testbench(self):
        self.p = Reg(E)

        self.x = Reg(Bool)
        self.y = Reg(Bool)
        self.z = Reg(UInt(32))

        with self.p.A as a:
            self.x[:] = a.x
            self.y[:] = a.y

        with self.p.B as b:
            self.z[:] += b.z

        yield

        self.p[:] = E.C
        self.z[:] = 0

        yield self.clk

        self.p[:] = E.A(x=False, y=False)

        yield self.clk

        assert self.z.value == 0

        self.p[:] = E.B(z=3)

        yield self.clk

        assert self.z.value == 0
        assert self.x.value is False
        assert self.y.value is False

        self.p[:] = E.B(z=1)

        yield self.clk

        assert self.z.value == 3
        assert self.x.value is False
        assert self.y.value is False

        self.p[:] = E.A(x=True, y=False)

        yield self.clk

        assert self.z.value == 4
        assert self.x.value is False
        assert self.y.value is False

        yield self.clk

        assert self.z.value == 4
        assert self.x.value is True
        assert self.y.value is False
