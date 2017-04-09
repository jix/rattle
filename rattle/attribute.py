class Attribute:
    pass


class BuildAttribute(Attribute):
    pass


class VerilogSignalAttribute(Attribute):
    def __init__(self, signal, attribute):
        self.signal, self.attribute = signal, attribute


class VerilogParameters(Attribute):
    def __init__(self, parameters):
        self.parameters = parameters


class DoNotGenerate(Attribute):
    pass


class SimulationOnly(Attribute):
    pass


class ModuleName(Attribute):
    def __init__(self, name):
        self.name = name


class IO(BuildAttribute):
    def __init__(self, signal, pin, **attributes):
        self.signal, self.pin, self.attributes = signal, pin, attributes


class Keep(BuildAttribute):
    def __init__(self, signal):
        self.signal = signal


__all__ = [
    'Attribute',
    'VerilogSignalAttribute',
    'VerilogParameters',
    'DoNotGenerate',
    'SimulationOnly',
    'ModuleName',
]
