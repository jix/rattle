import subprocess
import sys
import shlex
import textwrap
import pickle
from pathlib import Path

from .build import Build
from ..visitor import visitor
from ..attribute import BuildAttribute, IO, Keep, VerilogSignalAttribute


class UcfConstraint(BuildAttribute):
    def __init__(self, *constraints, **fields):
        self.constraints, self.fields = constraints, fields


class IseBuild(Build):
    # pylint: disable=function-redefined
    def __init__(self, construct, part):
        self.part = part

        super().__init__(construct)

    def generate_sources(self):
        self.constraints = []

        super().generate_sources()

        with (self.build_dir / 'constraints.ucf').open('w') as file:
            for line in self.constraints:
                file.write(line)
                file.write('\n')

    @visitor
    def process_attribute(self, attribute, module):
        super().process_attribute(attribute, module)

    @process_attribute.on(Keep)
    def process_attribute(self, attribute, module):
        return VerilogSignalAttribute(attribute.signal, 'KEEP="TRUE"')

    @process_attribute.on(IO)
    def process_attribute(self, attribute, module):
        constraint_suffix = ''

        for io_attr, value in attribute.attributes.items():
            if io_attr == 'io_standard':
                constraint_suffix += ' | IOSTANDARD=%s' % value
            else:
                raise RuntimeError(
                    'unknown IO attribute %r' % io_attr)

        for path, pin in self.io_constraint_helper(attribute, module):
            self.constraints.append(
                'NET "%s" LOC=%s%s;' % (path, pin, constraint_suffix))

    @process_attribute.on(UcfConstraint)
    def process_attribute(self, attribute, module):
        fields = {
            field: self.str(value)
            for field, value in attribute.fields.items()}
        for constraint in attribute.constraints:
            self.constraints.append(constraint.format(**fields) + ';')

    def build(self):
        self.get_ise_environment()

        self.run_synthesis()
        self.run_map()
        self.run_par()
        self.run_bitgen()

    def run_synthesis(self):
        with self.enter_dir(self.build_dir / 'ise'):
            with open('xst.resp', 'w') as resp:
                resp.write(textwrap.dedent('''
                    run
                    -ifn xst.prj
                    -top {top}
                    -ofn synthesis_out.ngc
                    -ofmt NGC
                    -p {part}
                    -opt_mode speed
                    -opt_level 1
                ''')[1:].format(top=self.top_module_name, part=self.part))

            with open('xst.prj', 'w') as prj:
                for file in self.verilog_files:
                    try:
                        file = Path('..') / file.relative_to(self.build_dir)
                    except ValueError:
                        pass

                    prj.write('verilog work %s\n' % file)

            self.run_cmd(['xst', '-ifn', 'xst.resp'])

    def run_map(self):
        with self.enter_dir(self.build_dir / 'ise'):
            self.run_cmd([
                'ngdbuild', '-intstyle', 'ise', '-nt', 'timestamp',
                '-uc', self.build_dir / 'constraints.ucf',
                '-p', self.part, 'synthesis_out.ngc', 'map_in.ngd'])

            self.run_cmd([
                'map', '-intstyle', 'ise', '-p', self.part,
                '-mt', 'on', '-pr', 'b', '-w', '-o', 'map_out', 'map_in.ngd'])

    def run_par(self):
        with self.enter_dir(self.build_dir / 'ise'):
            self.run_cmd([
                'par', '-w', '-mt', 'on', '-intstyle', 'ise',
                '-ol', 'std', 'map_out.ncd', 'par_out.ncd'
            ])

    def run_bitgen(self):
        with self.enter_dir(self.build_dir / 'ise'):
            self.run_cmd([
                'bitgen', '-w', 'par_out.ncd', '../bitstream.bit'
            ])

    def get_ise_environment(self):
        get_env_src = textwrap.dedent('''
            import pickle, os, sys
            sys.stdout.buffer.write(b'--env--')
            pickle.dump(dict(os.environ), sys.stdout.buffer)
        ''')[1:]

        env = subprocess.check_output([
            'sh', '-c', '. /opt/Xilinx/14.7/ISE_DS/settings64.sh; ' +
            shlex.quote(sys.executable) + ' -c ' +
            shlex.quote(get_env_src)])

        self.env = pickle.loads(env.split(b'--env--', 1)[1])
