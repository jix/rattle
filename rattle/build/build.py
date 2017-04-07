import abc
import argparse
import subprocess
import os
from pathlib import Path

from ..verilog import Verilog
from ..attribute import Attribute, BuildAttribute
from ..primitive import PrimSlice, PrimStorage


class Build(metaclass=abc.ABCMeta):
    def __init__(self, construct):
        self.construct = construct
        self.top_module = None
        self.parser = argparse.ArgumentParser(
            description='Build a rattle project.',
            allow_abbrev=False)

        self.parser.add_argument(
            '-b', '--build-dir', metavar='DIR', default='build')
        self.parser.add_argument(
            '-G', '--no-generate', action='store_true')
        self.parser.add_argument(
            '-B', '--no-build', action='store_true')

        self.cli_main()

    @abc.abstractmethod
    def build(self):
        pass

    def construct_top_module(self):
        if self.top_module is None:
            self.top_module = self.construct()

            self.top_module._module_data.circuit.finalize()

            self.process_attributes(self.top_module)

    def process_attributes(self, module):
        new_attributes = []

        for submodule in module._module_data.submodules:
            self.process_attributes(submodule)

        for attribute in module._module_data.attributes:
            new_attribute = self.process_attribute(attribute, module)
            if new_attribute is None:
                new_attributes.append(attribute)
            elif isinstance(new_attribute, Attribute):
                new_attributes.append(new_attribute)
            else:
                new_attributes.extend(new_attribute)

        module._module_data.attributes = new_attributes

    @staticmethod
    def process_attribute(attribute, module):
        if isinstance(attribute, BuildAttribute):
            raise RuntimeError(
                'attribute %r in module %r not supported '
                'for the used toolchain' %
                (attribute, module))
        return attribute

    def generate_sources(self):
        self.construct_top_module()
        verilog_dir = self.build_dir / 'verilog'

        verilog_dir.mkdir(exist_ok=True)
        verilog_gen = Verilog(self.top_module)
        paths = verilog_gen.write_to_dir(verilog_dir)

        for file in verilog_dir.glob('*.v'):
            if file not in paths:
                file.unlink()

        self.verilog_files = sorted(paths)

        self.top_module_name = verilog_gen.module_name

        with (self.build_dir / 'top_module').open('w') as f:
            f.write('%s\n' % self.top_module_name)

    def use_existing_sources(self):
        verilog_dir = self.build_dir / 'verilog'

        self.verilog_files = sorted(verilog_dir.glob('*.v'))

        if not self.verilog_files:
            raise RuntimeError('No existing verilog sources found')

        try:
            self.top_module_name = (
                self.build_dir / 'top_module').read_text().strip()
        except FileNotFoundError:
            raise RuntimeError("The 'top_module' file is missing")

    def cli_main(self):
        self.args = self.parser.parse_args()

        self.build_dir = Path(self.args.build_dir).absolute()

        self.build_dir.mkdir(exist_ok=True)

        os.chdir(self.build_dir)

        if self.args.no_generate:
            self.use_existing_sources()
        else:
            self.generate_sources()

        if not self.args.no_build:
            self.build()

    def signal_paths(self, signal):
        for prim in signal._prims.values():
            if prim.width == 0:
                continue

            prim = prim.simplify_read()

            suffix = ''

            if isinstance(prim, PrimSlice):
                if prim.width == 1:
                    suffix = '[%i]' % prim.start
                else:
                    suffix = '[%i:%i]' % (
                        prim.start + prim.width - 1, prim.start)
                prim = prim.x

            if not isinstance(prim, PrimStorage):
                raise RuntimeError('cannot compute path for given signal')

            name = prim.module._module_data.names.name_prim(prim)

            yield self.module_path(prim.module, name + suffix), prim

    @staticmethod
    def module_path(module, *more):
        path = []

        current_module = module
        while current_module.parent is not None:
            module_name = current_module._module_data.name
            path.append(module_name)
            current_module = current_module._module_data.parent

        path.extend(more)
        return '.'.join(path)

    @staticmethod
    def run_cmd(cmd):
        subprocess.check_call(cmd)
