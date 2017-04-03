from rattle.prelude import *
from rattle.std.cdc import Synchronize
from .port import Port


class Rs232Rx(Module):
    def construct(self, bits=8, baudrate=None, fclk=None, period=None):
        if baudrate is None and fclk is None:
            pass
        elif baudrate is not None and fclk is not None:
            period_exact = fclk / baudrate

            period = round(period_exact)

            last_bit_delta = (
                abs(period - period_exact) * (bits + 1) + 1)

            if last_bit_delta > period / 4 or period < 4:
                raise ValueError('specified baudrate needs higher fclk')

            self.baudrate = fclk / period
        else:
            period = None

        if period is None:
            raise ValueError('specify either baudrate and fclk or period')

        self.rx = Input(Bool)
        self.source = OutputReg(Port(Bits(bits)))
        self.overflow = OutputReg(Bool)
        self.timer = Reg(UInt(log2up(period * 2)))
        self.bitpos = Reg(UInt(log2up(bits + 2)))

        self.sync_rx = Synchronize(Bool, reset_value=1)

        with reset:
            self.source.valid[:] = False
            self.bitpos[:] = 0
            self.overflow[:] = False

        self.source.valid[:] = False

        self.sync_rx.din[:] = self.rx

        self.timer_tick = self.timer + 1 == period * 2

        with when(self.timer_tick):
            self.timer[:] = period
        with otherwise:
            self.timer[:] += 1

        with when(self.bitpos == 0):
            with when(~self.sync_rx.dout):
                self.bitpos[:] += 1
                self.timer[:] = period // 2 + 1
        with elwhen(self.timer_tick):
            self.source.payload[:] >>= 1
            self.source.payload[-1][:] = self.sync_rx.dout
            with when(self.bitpos == bits):
                self.source.valid[:] = True

            with when(self.bitpos == bits + 1):
                self.bitpos[:] = 0
            with otherwise:
                self.bitpos[:] += 1

        with when(self.source.valid & ~self.source.ready):
            self.overflow[:] = True


class Rs232Tx(Module):
    def construct(self, bits=8, baudrate=None, fclk=None, period=None):
        if baudrate is None and fclk is None:
            pass
        elif baudrate is not None and fclk is not None:
            period_exact = fclk / baudrate

            period = round(period_exact)

            last_bit_delta = (
                abs(period - period_exact) * (bits + 1) + 1)

            if last_bit_delta > period / 4:
                raise ValueError('specified baudrate needs higher fclk')

            self.baudrate = fclk / period
        else:
            period = None

        if period is None:
            raise ValueError('specify either baudrate and fclk or period')

        self.tx = Output(Bool)
        self.sink = Input(Port(Bits(bits)))
        self.timer = Reg(UInt(log2up(period)))
        self.shiftreg = Reg(Bits(bits + 1))
        self.bitpos = Reg(UInt(log2up(bits + 2)))

        with reset:
            self.bitpos[:] = 0
            self.shiftreg[:] = 1
            self.timer[:] = period - 1

        self.tx[:] = self.shiftreg[0]

        self.timer_tick = self.timer + 1 == period

        with when(self.timer_tick):
            self.timer[:] = 0
        with otherwise:
            self.timer[:] += 1

        with when(self.timer_tick):
            self.shiftreg[:] >>= 1
            self.shiftreg[-1][:] = 1

        self.sink.ready[:] = (self.bitpos == 0) & self.timer_tick

        with when(self.timer_tick):
            with when(self.bitpos == 0):
                with when(self.sink.valid):
                    self.shiftreg[0][:] = 0
                    self.shiftreg[1:][:] = self.sink.payload
                    self.bitpos[:] = 1
                with otherwise:
                    self.timer[:] = period - 1
            with elwhen(self.bitpos == bits + 1):
                self.bitpos[:] = 0
            with otherwise:
                self.bitpos[:] += 1


class Rs232(Module):
    def construct(self, bits=8, baudrate=None, fclk=None, period=None):
        self.rx = Input(Bool)
        self.tx = Output(Bool)
        self.source = Output(Port(Bits(bits)))
        self.sink = Input(Port(Bits(bits)))
        self.overflow = Output(Bool)

        self.rx_mod = Rs232Rx(bits, baudrate, fclk, period)
        self.tx_mod = Rs232Tx(bits, baudrate, fclk, period)

        self.rx_mod.rx[:] = self.rx
        self.overflow[:] = self.rx_mod.overflow
        self.source[:] = self.rx_mod.source

        self.tx[:] = self.tx_mod.tx
        self.tx_mod.sink[:] = self.sink


__all__ = [
    'Rs232Rx',
    'Rs232Tx',
    'Rs232',
]
