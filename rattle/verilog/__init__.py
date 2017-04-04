import io
import os
from itertools import product
from collections import OrderedDict
from ..circuit import BlockAssign, BlockCond
from ..visitor import visitor
from ..attribute import (
    SimulationOnly, DoNotGenerate, ModuleName,
    VerilogParameters, VerilogSignalAttribute)
from .templates import VerilogTemplates


def _mark_last(i):
    i = iter(i)
    try:
        val = next(i)
    except StopIteration:
        return
    for next_val in i:
        yield False, val
        val = next_val
    yield True, val


class ModuleSources:
    def __init__(self):
        self.sources = OrderedDict()
        self.names = set()


class Verilog(VerilogTemplates):
    # pylint: disable=function-redefined

    def __init__(self, module, module_sources=None):
        # TODO make this adjustable / include parameters
        self.module_name = type(module).__name__
        self.module = module
        self.module_data = module._module_data
        self.circuit = self.module_data.circuit
        self.names = self.module_data.names
        self.out = io.StringIO()
        self.indent = 0
        self.start_of_line = True
        self.submodule_verilogs = {}
        self.do_not_generate = False
        self.parameters = None
        self.signal_attributes = {}
        if module_sources is None:
            self.module_sources = ModuleSources()
        else:
            self.module_sources = module_sources

        self._process_attributes()

        if self.do_not_generate:
            return
        elif self.parameters is not None:
            raise RuntimeError(
                'verilog parameters are not supported for generated modules')

        self._process_submodules()
        self.circuit.finalize()
        self._prepare()
        self._emit()
        self._store()

    def write_to_dir(self, path):
        # TODO escape filenames?
        paths = []
        try:
            os.mkdir(path)
        except FileExistsError:
            pass
        for ((_type, source), name) in self.module_sources.sources.items():
            source_path = os.path.join(path, '%s.v' % name)
            paths.append(source_path)
            with open(source_path, 'w') as file:
                file.write('module %s' % name)
                file.write(source)
        return paths

    def _process_attributes(self):
        for attribute in self.module_data.attributes:
            self._attribute(attribute)

    @visitor
    def _attribute(self, attribute):
        pass

    @_attribute.on(SimulationOnly)
    def _attribute(self, attribute):
        # pylint: disable=no-self-use
        raise RuntimeError('Module %r is only for simulation' % self.module)

    @_attribute.on(DoNotGenerate)
    def _attribute(self, attribute):
        self.do_not_generate = True

    @_attribute.on(ModuleName)
    def _attribute(self, attribute):
        self.module_name = attribute.name

    @_attribute.on(VerilogParameters)
    def _attribute(self, attribute):
        self.parameters = attribute.parameters

    @_attribute.on(VerilogSignalAttribute)
    def _attribute(self, attribute):
        for prim in attribute.signal._prims.values():
            prim = prim.simplify_read()
            attributes = self.signal_attributes.setdefault(prim, [])
            attributes.append(attribute.attribute)

    def _process_submodules(self):
        for submodule in self.module_data.submodules:
            self.submodule_verilogs[submodule] = Verilog(
                submodule, self.module_sources)

    def _prepare(self):
        self.io_vecs = [
            prim for prim in self.module_data.io_prims if prim.dimensions]

        self.non_io_storage = [
            prim for prim in self.module_data.storage_prims
            if prim.direction is None]

        self.submodule_io = []

        self.reg_storage = set()
        self.wire_storage = set()

        self.named_prims = set()
        self.named_subexprs = []
        self.read_prims = set()

        self.named_prims.update(self.module_data.storage_prims)

        self.storage = set(self.module_data.storage_prims)

        for submodule in self.module_data.submodules:
            submodule_io = submodule._module_data.io_prims
            self.named_prims.update(submodule_io)
            self.submodule_io.extend(submodule_io)
            self.storage.update(submodule_io)

        for storage, assignments in self.circuit.assign.items():
            self.wire_storage.add(storage)
            for _lvalue, rvalue in assignments:
                self._prepare_expr(rvalue)

        for _storage, block in self.circuit.combinational.items():
            self._prepare_block(block)

        for clock, block in self.circuit.clocked.items():
            self._prepare_expr(clock, named=True)
            self._prepare_block(block)

        if self.reg_storage & self.wire_storage:
            raise RuntimeError(
                'storage cannot be wire and reg at the same time')

    def _prepare_block(self, block):
        self.reg_storage.update(block.storage)
        self._prepare_block_assignments(block.assignments)

    def _prepare_block_assignments(self, assignments):
        for assignment in assignments:
            if isinstance(assignment, BlockAssign):
                self._prepare_expr(assignment.rvalue)
            elif isinstance(assignment, BlockCond):
                self._prepare_expr(assignment.condition)
                self._prepare_block_assignments(assignment.true)
                self._prepare_block_assignments(assignment.false)
            else:
                assert False

    def _prepare_expr(self, expr, named=False, indexable=False):
        if expr in self.named_prims:
            return
        elif expr in self.read_prims and not expr.dimensions:
            self.named_prims.add(expr)
            self.named_subexprs.append(expr)
        else:
            tokens, mode, _prec = self._expr_template(expr)

            if mode == 'assign':
                named = True

            if indexable and mode != 'indexable':
                named = True

            for token in tokens:
                if isinstance(token, str):
                    continue
                subexpr, submode, _prec = token
                self._prepare_expr(
                    subexpr,
                    named=submode == 'named',
                    indexable=submode == 'indexable')

            if named:
                self.named_prims.add(expr)
                self.named_subexprs.append(expr)

            if not self._expr_is_simple(expr):
                self.read_prims.add(expr)

    def _emit(self):
        self._emit_io_ports()
        self._emit_io_vec_decls()
        self._emit_storage_decls()
        self._emit_submodule_io_decls()
        self._emit_subexpr_decls()

        self._emit_submodule_instances()

        self._emit_io_vec_assigns()
        self._emit_subexpr_assigns()
        self._emit_assigns()

        self._emit_initial()
        self._emit_combinational()
        self._emit_clocked()

        if self.circuit.async_reset:
            raise RuntimeError('async reset not implemented yet')

        self.indent -= 1
        self._writeln('endmodule')

        self.source = self.out.getvalue()

    def _writeln(self, *args):
        self._write(*args)
        self.out.write('\n')
        self.start_of_line = True

    def _write(self, *args):
        if args:
            if self.start_of_line:
                self.out.write('    ' * self.indent)
            for arg in args:
                self.out.write(str(arg))
            self.start_of_line = False

    def _write_block(self, block):
        lines = block.split('\n')
        for last, line in _mark_last(lines):
            if last:
                self._write(line)
            else:
                self._writeln(line)

    def _emit_io_ports(self):
        if not self.module_data.io_prims:
            self._writeln('();')
            return

        self._writeln('(')
        self.indent += 1
        for last, port in _mark_last(self.module_data.io_prims):
            if port in self.reg_storage and not port.dimensions:
                storage = ' reg '
            else:
                storage = ' '

            if port.width == 1:
                width = ''
            else:
                width = '[%i:0] ' % (port.width - 1)

            indices = product(*map(range, reversed(port.dimensions)))

            index_fmt = '_%i' * len(port.dimensions)

            name = self.names.name_prim(port)

            for last_index, index in _mark_last(indices):
                if last and last_index:
                    comma = ''
                else:
                    comma = ','
                self._writeln(
                    port.direction, storage, width,
                    name, index_fmt % index, comma)
        self.indent -= 1
        self._writeln(');')
        self.indent += 1

    def _emit_io_vec_decls(self):
        if not self.io_vecs:
            return
        self._writeln('// vector io port declarations')
        for port in self.io_vecs:
            self._emit_decl(port)
        self._writeln()

    def _emit_io_vec_assigns(self):
        if not self.io_vecs:
            return
        self._writeln('// vector io port assignments')
        for port in self.io_vecs:
            indices = product(*map(range, reversed(port.dimensions)))

            suffix_fmt = '_%i' * len(port.dimensions)
            index_fmt = '[%i]' * len(port.dimensions)

            name = self.names.name_prim(port)

            for index in indices:
                if port.direction == 'input':
                    self._writeln(
                        'assign ',
                        name, index_fmt % index, ' = ',
                        name, suffix_fmt % index, ';')
                elif port.direction == 'output':
                    self._writeln(
                        'assign ',
                        name, suffix_fmt % index, ' = ',
                        name, index_fmt % index, ';')
        self._writeln()

    def _emit_storage_decls(self):
        if not self.non_io_storage:
            return
        self._writeln('// storage signal declaration')
        for prim in self.non_io_storage:
            self._emit_decl(prim)
        self._writeln()

    def _emit_submodule_io_decls(self):
        if not self.submodule_io:
            return
        self._writeln('// submodule io port declarations')
        for port in self.submodule_io:
            self._emit_decl(port)
        self._writeln()

    def _emit_subexpr_decls(self):
        if not self.named_subexprs:
            return
        self._writeln('// temporary signal declarations')
        for prim in self.named_subexprs:
            self._emit_decl(prim)
        self._writeln()

    def _emit_decl(self, prim):
        try:
            attributes = self.signal_attributes[prim]
            del self.signal_attributes[prim]
        except KeyError:
            pass
        else:
            for attribute in attributes:
                self._write('(* ', attribute, ' *) ')
        if prim in self.reg_storage:
            storage = 'reg '
        else:
            storage = 'wire '

        if prim.width == 1:
            width = ''
        else:
            width = '[%i:0] ' % (prim.width - 1)

        vec_fmt = ' [%i:0]' * len(prim.dimensions)
        vec = vec_fmt % tuple(dim - 1 for dim in reversed(prim.dimensions))

        self._writeln(storage, width, self.names.name_prim(prim), vec, ';')

    def _emit_submodule_instances(self):
        if not self.module_data.submodules:
            return
        self._writeln('// module instantiations')
        for submodule, verilog in self.submodule_verilogs.items():
            submodule_data = submodule._module_data
            self._write(verilog.module_name, ' ')
            if verilog.parameters is not None:
                self._write('#(')
                self.indent += 1
                self._write_block(verilog.parameters)
                self.indent -= 1
                self._write(') ')
            self._write(self.names.name_submodule(submodule))
            if submodule_data.io_prims:
                self._writeln('(')
                self.indent += 1
                for last_port, port in _mark_last(submodule_data.io_prims):
                    indices = product(*map(range, reversed(port.dimensions)))

                    suffix_fmt = '_%i' * len(port.dimensions)
                    index_fmt = '[%i]' * len(port.dimensions)

                    for last_index, index in _mark_last(indices):
                        sep = '' if last_port and last_index else ','
                        self._writeln(
                            '.', submodule_data.names.name_prim(port),
                            suffix_fmt % index,
                            '(', self.names.name_prim(port),
                            index_fmt % index, ')', sep)
                self.indent -= 1
                self._writeln(');')
            else:
                self._writeln('();')

            self._writeln()

    def _emit_subexpr_assigns(self):
        if not self.named_subexprs:
            return
        self._writeln('// temporary signals')
        for prim in self.named_subexprs:
            self._write('assign ', self.names.name_prim(prim), ' = ')
            self._emit_expr(prim, expand=True)
            self._writeln(';')
        self._writeln()

    def _emit_assigns(self):
        if not self.circuit.assign:
            return
        self._writeln('// continuous assignments')
        for _storage, assigns in self.circuit.assign.items():
            for lvalue, rvalue in assigns:
                self._write('assign ')
                self._emit_expr(lvalue, lvalue=True)
                self._write(' = ')
                self._emit_expr(rvalue)
                self._writeln(';')
        self._writeln()

    def _emit_initial(self):
        if not self.circuit.initial:
            return
        self._writeln('// initial assignments')
        for _storage, block in self.circuit.initial.items():
            self._writeln('initial begin')
            self.indent += 1
            self._emit_block_assignments(block.assignments)
            self.indent -= 1
            self._writeln('end')
            self._writeln()

    def _emit_combinational(self):
        if not self.circuit.combinational:
            return
        self._writeln('// combinational processes')
        for _storage, block in self.circuit.combinational.items():
            self._writeln('always @ (*) begin')
            self.indent += 1
            self._emit_block_assignments(block.assignments)
            self.indent -= 1
            self._writeln('end')
            self._writeln()

    def _emit_clocked(self):
        if not self.circuit.clocked:
            return
        self._writeln('// clocked processes')
        for clock, block in self.circuit.clocked.items():
            clock_name = self.names.name_prim(clock)
            self._writeln('always @ (posedge ', clock_name, ') begin')
            self.indent += 1
            self._emit_block_assignments(block.assignments)
            self.indent -= 1
            self._writeln('end')
            self._writeln()

    def _emit_block_assignments(self, assignments):
        for assignment in assignments:
            if isinstance(assignment, BlockCond):
                self._write('if (')
                self._emit_expr(assignment.condition)
                self._writeln(') begin')
                self.indent += 1
                self._emit_block_assignments(assignment.true)
                self.indent -= 1
                else_part = assignment.false
                if not else_part:
                    self._writeln('end')
                elif (
                        len(else_part) == 1 and
                        isinstance(else_part[0], BlockCond)):
                    self._write('end else ')
                    self._emit_block_assignments(else_part)
                else:
                    self._writeln('end else begin')
                    self.indent += 1
                    self._emit_block_assignments(else_part)
                    self.indent -= 1
                    self._writeln('end')
            elif isinstance(assignment, BlockAssign):
                self._emit_expr(assignment.lvalue, lvalue=True)
                self._write(' <= ')
                self._emit_expr(assignment.rvalue)
                self._writeln(';')
            else:
                assert False

    def _emit_expr(self, prim, lvalue=False, expand=False, mode=None, prec=99):
        if lvalue:
            named = prim in self.storage
        else:
            named = prim in self.named_prims and not expand
        if named:
            self._write(self.names.name_prim(prim))
            return
        tokens, expr_mode, expr_prec = self._expr_template(prim)
        parens = '()' if expr_prec > prec else False
        if expr_mode == 'context' and mode == 'no-context':
            parens = '{}'
        if parens:
            self._write(parens[0])
        for token in tokens:
            if isinstance(token, str):
                self._write(token)
            else:
                subexpr, submode, subprec = token
                self._emit_expr(subexpr, mode=submode, prec=subprec)
        if parens:
            self._write(parens[1])

    def _store(self):
        source_id = (type(self.module), self.source)
        try:
            self.module_name = self.module_sources.sources[source_id]
            return
        except KeyError:
            pass

        unique_name = self.module_name
        counter = 0
        while unique_name in self.module_sources.names:
            counter += 1
            unique_name = '%s_%i' % (self.module_name, counter)
        self.module_name = unique_name

        self.module_sources.sources[source_id] = self.module_name
        self.module_sources.names.add(self.module_name)
