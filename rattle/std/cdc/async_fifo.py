from rattle.prelude import *
from ..port import Port
from .synchronize import Synchronize


class AsyncFifo(Module):
    def construct(self, payload_type, size, sink_clk, source_clk):
        if payload_type.contains_flipped:
            raise TypeError(
                'AsyncFifo does not support bidirectional payload types')

        if not ispow2(size):
            raise ValueError(
                'AsyncFifo size must be a power of two')

        addr_width = log2up(size)

        Ptr = UInt(addr_width + 1)

        # TODO replace this with sth like an ImplicitInput
        self.sink_clk = Input(sink_clk.signal_type)
        self.source_clk = Input(source_clk.signal_type)
        with self.parent.reopen():
            self.sink_clk[:] = sink_clk
            self.source_clk[:] = source_clk

        self.sink = Input(Port(payload_type))
        self.source = Output(Port(payload_type))

        with self.sink_clk:
            self.memory = Reg(Vec(size, Packed(payload_type)))
            self.write_ptr = Reg(Ptr)
            self.write_ptr_next = Reg(Ptr)
            self.write_ptr_gray = Reg(Ptr)
            self.read_ptr_gray_synced = Wire(Ptr)
            self.write_data = Wire(Packed(payload_type))

        with self.source_clk:
            self.read_ptr = Reg(Ptr)
            self.read_ptr_next = Reg(Ptr)
            self.read_ptr_gray = Reg(Ptr)
            self.write_ptr_gray_synced = Wire(Ptr)
            self.read_data = Reg(Packed(payload_type))
            self.read_valid = Reg(Bool)

        with reset:
            self.read_ptr[:] = 0
            self.read_ptr_gray[:] = 0
            self.read_ptr_next[:] = 1
            self.write_ptr[:] = 0
            self.write_ptr_gray[:] = 0
            self.write_ptr_next[:] = 1
            self.read_valid[:] = False

        with self.sink_clk:
            self.sync_read_ptr = Synchronize(Ptr, reset_value=0)
            self.sync_read_ptr.din[:] = self.read_ptr_gray
            self.read_ptr_gray_synced[:] = self.sync_read_ptr.dout

        with self.source_clk:
            self.sync_write_ptr = Synchronize(Ptr, reset_value=0)
            self.sync_write_ptr.din[:] = self.write_ptr_gray
            self.write_ptr_gray_synced[:] = self.sync_write_ptr.dout

        # read

        self.data_to_read = self.read_ptr_gray != self.write_ptr_gray_synced
        self.perform_read = self.data_to_read & (
            ~self.read_valid | self.source.ready)

        with when(self.source.active):
            self.read_valid[:] = False

        with when(self.perform_read):
            self.read_ptr_gray[:] = (
                self.read_ptr_next ^ (self.read_ptr_next >> 1))
            self.read_ptr[:] = self.read_ptr_next
            self.read_ptr_next[:] += 1
            self.read_data[:] = self.memory[self.read_ptr]
            self.read_valid[:] = self.data_to_read

        self.source.payload[:] = self.read_data
        self.source.valid[:] = self.read_valid

        # write

        self.sink.ready[:] = self.read_ptr_gray_synced != (
            self.write_ptr_gray ^ size ^ (size >> 1))

        self.write_data[:] = self.sink.payload

        with when(self.sink.active):
            self.memory[self.write_ptr][:] = self.write_data
            self.write_ptr_gray[:] = (
                self.write_ptr_next ^ (self.write_ptr_next >> 1))
            self.write_ptr[:] = self.write_ptr_next
            self.write_ptr_next[:] += 1


__all__ = [
    'AsyncFifo',
]
