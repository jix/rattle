import re

from .build import Build
from ..visitor import visitor
from ..attribute import IO, Keep, VerilogSignalAttribute


class IcestormBuild(Build):
    # pylint: disable=abstract-method
    # pylint: disable=function-redefined
    def __init__(self, construct, part):
        self.part = part

        if part.startswith('lp') or part.startswith('hx'):
            self.part_speed = part[:2]
            part = part[2:]
        else:
            self.part_speed = None

        if '-' in part:
            self.part_size, self.part_package = part.split('-')
        else:
            self.part_size = part
            self.part_package = None

        super().__init__(construct)

    def generate_sources(self):
        self.constraints = []

        super().generate_sources()

        with (self.build_dir / 'constraints.pcf').open('w') as file:
            for line in self.constraints:
                file.write(line)
                file.write('\n')

    @visitor
    def process_attribute(self, attribute, module):
        super().process_attribute(attribute, module)

    @process_attribute.on(Keep)
    def process_attribute(self, attribute, module):
        return VerilogSignalAttribute(attribute.signal, 'keep=1')

    @process_attribute.on(IO)
    def process_attribute(self, attribute, module):
        if module is not self.top_module:
            raise RuntimeError(
                'IO constraints are only allowed in the top level module')
        paths = list(self.signal_paths(attribute.signal))
        if len(paths) != 1:
            raise RuntimeError(
                'IO constraints are not allowed for composite signals')

        path, prim = paths[0]

        pins = attribute.pin.split()

        if prim.width != len(pins):
            raise RuntimeError('mismatch between signal width and pin count')

        if prim.width == 1:
            self.constraints.append(
                'set_io %s %s' % (path, pins[0]))
        else:
            for i, pin in enumerate(pins):
                self.constraints.append(
                    'set_io %s[%i] %s' % (path, i, pin))

    def build(self):
        self.run_cmd([
            'yosys', '-q', '-p', 'synth_ice40 -blif synthesis_out.blif',
            *map(str, self.verilog_files)])

        if self.part_package is None:
            part_package = []
        else:
            part_package = ['-P', self.part_package]

        self.run_cmd([
            'arachne-pnr', '-d', self.part_size, *part_package,
            '-p', 'constraints.pcf', 'synthesis_out.blif',
            '-o', 'pnr_out.txt'])

        self.run_cmd(['icepack', 'pnr_out.txt', 'bitstream.bin'])
