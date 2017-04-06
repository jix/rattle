from rattle.prelude import *
from rattle.attribute import VerilogSignalAttribute


class Synchronize(Module):
    def construct(self, signal_type, reset_value=None, stages=2):
        self.din = Input(signal_type)
        self.dout = Output(signal_type)

        self.regs = Reg(Vec(stages, signal_type))

        if reset_value is not None:
            with reset:
                for reg in self.regs:
                    reg[:] = reset_value

        for current_reg, next_reg in zip(self.regs, self.regs[1:]):
            next_reg[:] = current_reg

        self.regs[0][:] = self.din
        self.dout[:] = self.regs[-1]

        # TODO This is xilinx specific, change to generic attribute
        self.attribute(VerilogSignalAttribute(self.regs, 'KEEP="TRUE"'))
