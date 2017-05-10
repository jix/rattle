import subprocess
import sys
import shlex
import textwrap
import pickle
import re
import hashlib
from contextlib import contextmanager
from pathlib import Path

from .ipcore import IpCore
from ..build import Build
from ...visitor import visitor
from ...attribute import BuildAttribute, IO, Keep, VerilogSignalAttribute


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

        self.clear_dir(self.build_dir / 'ipcore')

        self.postprocess_module(self.top_module)

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

    @visitor
    def postprocess_module(self, module):
        for submodule in module._module_data.submodules:
            self.postprocess_module(submodule)

    @postprocess_module.on(IpCore)
    def postprocess_module(self, module):
        ipcore_dir = self.build_dir / 'ipcore'
        ipcore_dir.mkdir(exist_ok=True)

        name = module._module_data.module_name

        with (ipcore_dir / ('%s.tcl' % name)).open('w') as script_file:
            script_file.write(
                'set ipcore_name %s\n' % self.tcl_escape(name))
            script_file.write(module._ipcore_script)
            script_file.write('\n')
            script_file.write(
                'set_property generate_synth_checkpoint false'
                ' [get_files [get_property IP_FILE [get_ips $ipcore_name]]]\n')
            script_file.write(
                'generate_target synthesis'
                ' [get_files [get_property IP_FILE [get_ips $ipcore_name]]]\n')

    def build(self):
        project_dir = self.build_dir / 'vivado'

        self.clear_dir(project_dir)

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

        for file in sorted((self.build_dir / 'ipcore').glob('*.tcl')):
            self.vivado_cmd('source -notrace %s' % self.tcl_escape(
                Path('..') / file.relative_to(self.build_dir)))

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
            cwd=str(self.build_dir),
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
            self.get_vivado_environment()
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

    def get_ipcore_xml(self, ipcore_script):
        script_hash = hashlib.sha224(ipcore_script.encode('utf-8')).hexdigest()

        try:
            return self.cache_get('ipcore', script_hash)
        except KeyError:
            pass

        tmp_dir = self.build_dir / 'vivado_tmp'

        tmp_dir.mkdir(exist_ok=True)

        script_path = tmp_dir / 'ipcore.tcl'

        with script_path.open('w') as script_file:
            script_file.write('set ipcore_name ipcore\n')
            script_file.write(ipcore_script)
            script_file.write('\n')
            script_file.write('return [get_property IP_FILE [get_ips ipcore]]')

        self.vivado_cmd('cd %s' % self.tcl_escape(tmp_dir))

        self.vivado_cmd(
            'create_project -in_memory -part %s tmp_project .' %
            self.tcl_escape(self.part))

        xci_path = Path(self.vivado_cmd('source -notrace ipcore.tcl'))

        with xci_path.with_suffix('.xml').open('rb') as xml_file:
            xml = xml_file.read()

        self.vivado_cmd('close_project')
        self.vivado_cmd('cd %s' % self.tcl_escape(self.build_dir))

        self.clear_dir(tmp_dir)

        self.cache_put('ipcore', script_hash, xml)

        return xml

    def cache_put(self, cache, key, value):
        cache_dir = self.build_dir / 'cache' / cache
        cache_dir.mkdir(exist_ok=True, parents=True)

        with (cache_dir / key).open('wb') as file:
            file.write(value)

    def cache_get(self, cache, key):
        try:
            with (self.build_dir / 'cache' / cache / key).open('rb') as file:
                return file.read()
        except FileNotFoundError:
            pass
        raise KeyError('no cache entry found in %s cache' % cache)


__all__ = [
    'XdcConstraint',
    'VivadoBuild',
]
