import abc
import argparse
import subprocess
import os
import shutil
from contextlib import contextmanager
from pathlib import Path

from ..verilog import Verilog
from ..attribute import Attribute, BuildAttribute
from ..primitive import PrimSlice, PrimStorage
from ..signal import Signal
from ..module import Module
from ..type import Bits
from .. import context


class Build(metaclass=abc.ABCMeta):
    def __init__(self, construct):
        self.construct = construct
        self.top_module = None
        self.env = None

        self.parser = argparse.ArgumentParser(
            description='Build a rattle project.',
            allow_abbrev=False)

        self.parser.add_argument(
            '-b', '--build-dir', metavar='DIR', default='build')
        self.parser.add_argument(
            '-G', '--no-generate', action='store_true')
        self.parser.add_argument(
            '-B', '--no-build', action='store_true')

        with context.current().activate_build(self):
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

    def io_constraint_helper(self, attribute, module):
        if module is not self.top_module:
            raise RuntimeError(
                'IO constraints are only allowed in the top level module')

        if len(attribute.signal._prims) != 1:
            raise RuntimeError('expected non-composite signal')

        signal = Bits._prim(next(iter(attribute.signal._prims.values())))

        pins = attribute.pin.split()

        if signal.width != len(pins):
            raise RuntimeError(
                'mismatch between signal width (%i) and pin count (%i)' %
                (signal.width, len(pins)))

        if signal.width == 1:
            yield self.prim_path(signal._prim()), pins[0]
        else:
            for i, pin in enumerate(pins):
                yield self.prim_path(signal[i]._prim()), pin

    def str(self, value):
        if isinstance(value, Signal):
            return self.signal_path(value)
        elif isinstance(value, Module):
            return self.module_path(value)
        else:
            return str(value)

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

        self.top_module_name = self.top_module._module_data.module_name

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

        with self.enter_dir(self.build_dir):
            try:
                if self.args.no_generate:
                    self.use_existing_sources()
                else:
                    self.generate_sources()

                if not self.args.no_build:
                    self.build()
            finally:
                self.teardown()

    def teardown(self):
        pass

    def signal_path(self, signal):
        paths = list(self.signal_paths(signal))
        if len(paths) != 1:
            raise RuntimeError('expected non-composite signal')

        return paths[0]

    def signal_paths(self, signal):
        for prim in signal._prims.values():
            if prim.width == 0:
                continue

            yield self.prim_path(prim)

    def prim_path(self, prim):
        if prim.width == 0:
            raise RuntimeError('zero-width signal cannot be named')

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

        return self.module_path(prim.module, name + suffix)

    @staticmethod
    def module_path(module, *more):
        path = []

        current_module = module
        while current_module.parent is not None:
            module_name = current_module._module_data.instance_name
            path.append(module_name)
            current_module = current_module._module_data.parent

        path.extend(more)
        return '.'.join(path)

    def run_cmd(self, cmd):
        subprocess.check_call(cmd, env=self.env)

    @staticmethod
    @contextmanager
    def enter_dir(path, create=True):
        if create:
            path.mkdir(exist_ok=True)

        old_dir = os.getcwd()
        os.chdir(str(path))
        try:
            yield
        finally:
            os.chdir(old_dir)

    def clear_dir(self, path):
        path = Path(path)
        # This ensures we don't do nasty things by accident
        path.relative_to(self.build_dir)

        if path.exists():
            shutil.rmtree(str(path))
