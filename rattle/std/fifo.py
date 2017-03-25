from rattle.prelude import *
from .port import Port


class Fifo(Module):
    def construct(self, payload_type, size):
        if payload_type.contains_flipped:
            raise TypeError(
                'Fifo does not support bidirectional payload types')

        if not ispow2(size):
            raise ValueError(
                'Fifo size must be a power of two')

        addr_width = log2up(size)

        self.sink = Input(Port(payload_type))
        self.source = Output(Port(payload_type))

        self.memory = Reg(Vec(size, Packed(payload_type)))

        self.read_ptr = Reg(UInt(addr_width + 1))
        self.write_ptr = Reg(UInt(addr_width + 1))

        self.read_data = Reg(Packed(payload_type))
        self.read_valid = Reg(Bool)

        self.write_data = Wire(Packed(payload_type))

        with reset:
            self.read_ptr[:] = 0
            self.write_ptr[:] = 0
            self.read_valid[:] = False

        # read

        self.data_to_read = self.read_ptr != self.write_ptr
        self.perform_read = self.data_to_read & (
            ~self.read_valid | self.source.ready)

        with when(self.source.active):
            self.read_valid[:] = False

        with when(self.perform_read):
            self.read_ptr[:] += 1
            self.read_data[:] = self.memory[self.read_ptr]
            self.read_valid[:] = self.data_to_read

        self.source.payload[:] = self.read_data
        self.source.valid[:] = self.read_valid

        # write

        self.sink.ready[:] = self.read_ptr != self.write_ptr ^ size

        self.write_data[:] = self.sink.payload

        with when(self.sink.active):
            self.memory[self.write_ptr][:] = self.write_data
            self.write_ptr[:] += 1


__all__ = [
    'Fifo',
]
