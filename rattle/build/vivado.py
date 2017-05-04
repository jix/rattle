import subprocess
import sys
import shlex
import shutil
import textwrap
import pickle
import re
from contextlib import contextmanager
from pathlib import Path

from .build import Build
from ..visitor import visitor
from ..attribute import BuildAttribute, IO, Keep, VerilogSignalAttribute


class XdcConstraint(BuildAttribute):
    def __init__(self, *constraints, **fields):
        self.constraints, self.fields = constraints, fields


class VivadoBuild(Build):
    # pylint: disable=function-redefined
    def __init__(self, construct, part):
        self.part = part
        self.vivado = None

        super().__init__(construct)

    def generate_sources(self):
        self.constraints = []

        super().generate_sources()

        with (self.build_dir / 'constraints.xdc').open('w') as file:
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
        for path, pin in self.io_constraint_helper(attribute, module):
            escaped_path = self.tcl_escape(path)
            self.constraints.append(
                'set_property PACKAGE_PIN %s [get_ports %s]' %
                (self.tcl_escape(pin), escaped_path))
            for io_attr, value in attribute.attributes.items():
                self.constraints.append(
                    'set_property %s %s [get_ports %s]' % (
                        self.tcl_escape(io_attr.upper()),
                        self.tcl_escape(value),
                        escaped_path))

    @process_attribute.on(XdcConstraint)
    def process_attribute(self, attribute, module):
        fields = {
            field: self.str(value)
            for field, value in attribute.fields.items()}
        for constraint in attribute.constraints:
            self.constraints.append(constraint.format(**fields))

    def build(self):
        self.get_vivado_environment()
        project_dir = self.build_dir / 'vivado'

        if project_dir.exists():
            shutil.rmtree(str(project_dir))

        project_dir.mkdir()

        self.vivado_cmd('cd %s' % self.tcl_escape(str(project_dir)))

        self.vivado_cmd(
            'create_project -part %s rattle_project .' %
            self.tcl_escape(self.part))

        files = []

        for file in self.verilog_files:
            try:
                file = Path('..') / file.relative_to(self.build_dir)
            except ValueError:
                pass
            files.append(file)

        self.vivado_cmd(
            'add_files ' + ' '.join(map(self.tcl_escape, files)))

        self.vivado_cmd(
            'add_files -fileset constrs_1 ../constraints.xdc')

        self.vivado_cmd(
            'set_property top %s [get_filesets sources_1]' %
            self.tcl_escape(self.top_module_name))

        # TODO is this needed?
        self.vivado_cmd(
            'update_compile_order -fileset sources_1')

        self.launch_run('synth_1')
        self.launch_run('impl_1', to_step='write_bitstream')

    def launch_run(self, run_name, to_step=None):
        escaped_run_name = self.tcl_escape(run_name)
        if to_step is not None:
            self.vivado_cmd(
                'launch_run %s -to_step %s' %
                (escaped_run_name, self.tcl_escape(to_step)))
        else:
            self.vivado_cmd('launch_run %s' % escaped_run_name)
        self.vivado_cmd('wait_on_run %s' % escaped_run_name)
        progress = self.vivado_cmd(
            'get_property PROGRESS [get_runs %s]' % escaped_run_name)

        if progress != '100%':
            raise RuntimeError('error during vivado run %s' % run_name)

    @contextmanager
    def launch_vivado(self):
        self.vivado = subprocess.Popen(
            'vivado -nolog -nojournal -mode tcl'.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=self.env)

        self.vivado.stdin.write(textwrap.dedent('''
            proc rattle_build {args} {
                set status [catch {{*}$args} result]
                puts "///RATTLE BUILD/// result"
                puts "$status"
                puts "$result"
                puts "///RATTLE BUILD/// done"
            }
            puts "///RATTLE BUILD/// ready"
        ''')[1:])
        self.vivado.stdin.flush()

        while True:
            line = self.vivado.stdout.readline()
            if not line:
                raise RuntimeError("could not start vivado shell")
            elif line == '///RATTLE BUILD/// ready\n':
                break
            else:
                print(line[:-1])

    def terminate_vivado(self):
        self.vivado.terminate()
        self.vivado.wait(10)
        self.vivado.kill()
        self.vivado.wait()
        self.vivado = None

    def teardown(self):
        if self.vivado is not None:
            self.terminate_vivado()

    def vivado_cmd(self, command):
        if self.vivado is None:
            self.launch_vivado()

        print("> " + command)
        self.vivado.stdin.write('rattle_build %s\n' % command)
        self.vivado.stdin.flush()

        while True:
            line = self.vivado.stdout.readline()
            if not line:
                raise RuntimeError("unexpected EOF from Vivado")
            elif line == '///RATTLE BUILD/// result\n':
                break
            else:
                print(line[:-1])

        status = int(self.vivado.stdout.readline().strip())

        result = []

        while True:
            line = self.vivado.stdout.readline()
            if not line:
                raise RuntimeError("unexpected EOF from Vivado")
            elif line == '///RATTLE BUILD/// done\n':
                break
            else:
                result.append(line[:-1])

        result = '\n'.join(result)

        if status:
            raise RuntimeError("Vivado tcl error: %s" % result)

        return result

    @staticmethod
    def tcl_escape(string):
        return '"%s"' % re.subn(r'([\[\]{}\\$])', r'\\\1', str(string))[0]

    def get_vivado_environment(self):
        get_env_src = textwrap.dedent('''
            import pickle, os, sys
            sys.stdout.buffer.write(b'--env--')
            pickle.dump(dict(os.environ), sys.stdout.buffer)
        ''')[1:]

        env = subprocess.check_output([
            'sh', '-c', '. /opt/Xilinx/Vivado/2017.1/settings64.sh; ' +
            shlex.quote(sys.executable) + ' -c ' +
            shlex.quote(get_env_src)])

        self.env = pickle.loads(env.split(b'--env--', 1)[1])
