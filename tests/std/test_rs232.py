from rattle.prelude import *
from rattle.std.port import SimSource, SimSink
from rattle.std.rs232 import *
import rattle.sim as sim


def test_rs232rx(sim_testbench):
    @sim_testbench
    def _testbench(self):
        self.sink = SimSink(Bits(8))
        self.rx = Rs232Rx(baudrate=7800, fclk=100000)

        self.sink.sink[:] = self.rx.source

        yield

        period = round(1e6 / 7800)

        def write_bytes(data_bytes):
            for byte in data_bytes:
                bits = [0] + [byte & (1 << i) for i in range(8)] + [1]
                for bit in bits:
                    self.rx.rx[:] = bit
                    yield period

        test_data = b'Test!\xff\x55\xaa\x00'

        self.rx.rx[:] = 1

        yield from [self.clk] * 10

        sim.thread(lambda: write_bytes(test_data[:4]))

        yield from [self.clk] * 700

        sim.thread(lambda: write_bytes(test_data[4:]))

        yield from [self.clk] * 700

        assert bytes([x.as_uint().value for x in self.sink.items]) == test_data
        assert self.rx.overflow.value is False


def test_rs232_roundtrip(sim_testbench):
    @sim_testbench
    def _testbench(self):
        self.source = SimSource(Bits(8))
        self.sink = SimSink(Bits(8))
        self.rs232 = Rs232(baudrate=7800, fclk=100000)

        self.rs232.sink[:] = self.source.source
        self.sink.sink[:] = self.rs232.source

        self.rs232.rx[:] = self.rs232.tx

        yield

        test_data = b'Test!\xff\x55\xaa\x00'

        yield from [self.clk] * 3

        self.source.replace(test_data[:5])

        yield from [self.clk] * 700

        self.source.replace(test_data[5:])

        yield from [self.clk] * 700

        assert bytes([x.as_uint().value for x in self.sink.items]) == test_data
        assert self.rs232.overflow.value is False
