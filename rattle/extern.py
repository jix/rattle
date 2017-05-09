from .attribute import DoNotGenerate, ModuleName
from .module import Module
from .signal import Signal, Input
from .type import SignalType


class Extern(Module):
    def __init__(self, name, ios):
        self.attribute(DoNotGenerate(), ModuleName(name, unique=False))
        for io_name, direction, signal_or_type in ios:
            if isinstance(signal_or_type, Signal):
                assign = signal_or_type
                signal_type = signal_or_type.signal_type
            elif isinstance(signal_or_type, SignalType):
                assign = None
                signal_type = signal_or_type
            else:
                raise TypeError(
                    'expected Signal or SignalType in Extern port declaration')

            port = direction(signal_type)
            setattr(self, io_name, port)

            if assign is not None:
                with self.parent.reopen():
                    if direction is Input:
                        port[:] = assign
                    else:
                        assign[:] = port


__all__ = ['Extern']
