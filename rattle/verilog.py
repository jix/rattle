import io
from itertools import product


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


class Verilog:
    def __init__(self, module):
        self.module = module
        self.module_data = module._module_data
        self.circuit = self.module_data.circuit
        self.names = self.module_data.names
        self.out = io.StringIO()
        self.indent = 0
        self.start_of_line = True

        self.circuit.finalize()
        self._prepare()
        self._emit()

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

        for storage, assignments in self.circuit.assign.items():
            self.wire_storage.add(storage)
            for _target, source in assignments:
                self._prepare_expr(source)

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
            if assignment[0] == '=':
                _target, source = assignment[2:]
                self._prepare_expr(source)
            elif assignment[0] == '?':
                self._prepare_expr(assignment[1])
                self._prepare_block_assignments(assignment[2])
                self._prepare_block_assignments(assignment[3])

    def _prepare_expr(self, expr, named=False, indexable=False):
        if expr in self.named_prims:
            return
        elif expr in self.read_prims and not expr.dimensions:
            self.named_prims.add(expr)
            self.named_subexprs.append(expr)
        else:
            tokens, mode = expr.verilog_expr()

            if mode == 'assign':
                named = True

            if indexable and mode != 'indexable':
                named = True

            for token in tokens:
                if isinstance(token, str):
                    continue
                subexpr, submode = token
                self._prepare_expr(
                    subexpr,
                    named=submode == 'named',
                    indexable=submode == 'indexable')

            if named:
                self.named_prims.add(expr)
                self.named_subexprs.append(expr)

            if mode != 'const':
                self.read_prims.add(expr)

    def _emit(self):
        self._emit_io_ports()
        self._emit_io_vec_decls()
        self._emit_storage_decls()
        self._emit_submodule_io_decls()
        self._emit_subexpr_decls()

        # TODO submodule instantiations

        self._emit_io_vec_assigns()
        self._emit_subexpr_assigns()
        self._emit_assigns()

        self._emit_combinational()
        self._emit_clocked()

        if self.circuit.async_reset:
            raise RuntimeError('async reset not implemented yet')

        self.indent -= 1
        self._writeln('endmodule')

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

    def _emit_decl(self, port):
        if port in self.reg_storage:
            storage = 'reg '
        else:
            storage = 'wire '

        if port.width == 1:
            width = ''
        else:
            width = '[%i:0] ' % (port.width - 1)

        vec_fmt = ' [%i:0]' * len(port.dimensions)
        vec = vec_fmt % tuple(dim - 1 for dim in reversed(port.dimensions))

        self._writeln(storage, width, self.names.name_prim(port), vec, ';')

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
            for target, source in assigns:
                self._write('assign ')
                self._emit_expr(target, target=True)
                self._write(' = ')
                self._emit_expr(source)
                self._writeln('\n')
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
            if assignment[0] == '?':
                self._write('if (')
                self._emit_expr(assignment[1])
                self._writeln(') begin')
                self.indent += 1
                self._emit_block_assignments(assignment[2])
                self.indent -= 1
                self._writeln('end else begin')
                self.indent += 1
                self._emit_block_assignments(assignment[3])
                self.indent -= 1
                self._writeln('end')
            else:
                self._emit_expr(assignment[2], target=True)
                self._write(' <= ')
                self._emit_expr(assignment[3])
                self._writeln(';')

    def _emit_expr(self, prim, target=False, expand=False, parens=False):
        if target:
            named = prim in self.storage
        else:
            named = prim in self.named_prims and not expand
        if named:
            self._write(self.names.name_prim(prim))
            return
        tokens, mode = prim.verilog_expr()
        if mode == 'constant':
            parens = False
        if parens:
            self._write('(')
        for token in tokens:
            if isinstance(token, str):
                self._write(token)
            else:
                subexpr, submode = token
                self._emit_expr(subexpr, parens=submode != 'indexable')
        if parens:
            self._write(')')
