from rattle.prelude import *
from rattle.attribute import Keep


class Synchronize(Module):
    def __init__(self, signal_type, reset_value=..., stages=2):
        self.din = Input(signal_type)
        self.dout = Output(signal_type)

        init = ... if reset_value is ... else None

        self.regs = Reg(Vec(stages, signal_type), init=init)

        if reset_value is not None and init is None:
            with reset:
                for reg in self.regs:
                    reg[:] = reset_value

        for current_reg, next_reg in zip(self.regs, self.regs[1:]):
            next_reg[:] = current_reg

        self.regs[0][:] = self.din
        self.dout[:] = self.regs[-1]

        self.attribute(Keep(self.regs))
