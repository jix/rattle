class Vcd:
    def __init__(self, engine, trace, file):
        self._engine, self._trace, self._file = engine, trace, file

        self._vcd_ids = {}

        for _scope, _name, prim in self._trace._traces:
            if prim not in self._vcd_ids:
                # TODO more compact encoding of vcd ids
                self._vcd_ids[prim] = '%i' % len(self._vcd_ids)

        self._write_header()

    def update(self):
        # TODO dump incrementally
        self._write_time()
        self._dumpvars()

    def close(self):
        self.update()
        self._file.close()

    def _write_header(self):
        self._file.write('$version rattle sim $end\n')
        self._file.write('$timescale 1ns $end\n')  # TODO don't hardcode this
        for scope, name, prim in self._trace._traces:
            for scope_type, scope_name in scope:
                self._file.write(
                    '$scope %s %s $end\n' % (scope_type, scope_name))
            width = prim.width
            if width > 1:
                name = '%s[%i:0]' % (name, width - 1)
            vcd_id = self._vcd_ids[prim]
            self._file.write(
                '$var wire %i %s %s $end\n' % (width, vcd_id, name))
            for _scope_type, _scope_name in scope:
                self._file.write('$upscope $end\n')

        self._file.write('$enddefinitions $end\n')

    def _write_time(self):
        self._file.write('#%i\n' % self._engine.time())

    def _dumpvars(self):
        self._file.write('$dumpvars\n')
        for prim, vcd_id in self._vcd_ids.items():
            value = self._engine.peek(prim)
            self._dumpvar(vcd_id, value)
        self._file.write('$end\n')

    def _dumpvar(self, vcd_id, value):
        if value.width == 1:
            self._file.write('%s%s\n' % (value, vcd_id))
        else:
            self._file.write('b%s %s\n' % (value, vcd_id))
