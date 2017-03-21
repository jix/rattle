from itertools import count
from .primitive import PrimStorage


_reserved_names = set('''
alias always always_comb always_ff always_latch and assert assign assume
automatic before begin bind bins binsof bit break buf bufif0 bufif1 byte case
casex casez cell chandle class clocking cmos config const constraint context
continue cover covergroup coverpoint cross deassign default defparam design
disable dist do edge else end endcase endclass endclocking endconfig
endfunction endgenerate endgroup endinterface endmodule endpackage endprimitive
endprogram endproperty endspecify endsequence endtable endtask enum event
expect export extends extern final first_match for force foreach forever fork
forkjoin function generate genvar highz0 highz1 if iff ifnone ignore_bins
illegal_bins import incdir include initial inout input inside instance int
integer interface intersect join join_any join_none large liblist library local
localparam logic longint macromodule matches medium modport module nand negedge
new nmos nor noshowcancelled not notif0 notif1 null or output package packed
parameter pmos posedge primitive priority program property protected pull0
pull1 pulldown pullup pulsestyle_onevent pulsestyle_ondetect pure rand randc
randcase randsequence rcmos real realtime ref reg release repeat return rnmos
rpmos rtran rtranif0 rtranif1 scalared sequence shortint shortreal
showcancelled signed small solve specify specparam static string strong0
strong1 struct super supply0 supply1 table tagged task this throughout time
timeprecision timeunit tran tranif0 tranif1 tri tri0 tri1 triand trior trireg
type typedef union unique unsigned use uwire var vectored virtual void wait
wait_order wand weak0 weak1 while wildcard wire with within wor xnor xor
'''.split())


class Names:
    def __init__(self):
        self.used_names = set()
        self.prim_to_name = {}
        self.module_to_name = {}

    def name_signal(self, signal, name=None):
        all_named = True
        for prim in signal._prims.values():
            # TODO has simplify_read always the semantics we want here?
            prim = prim.simplify_read()
            if prim not in self.prim_to_name:
                all_named = False
                break
        if all_named:
            return

        # TODO better alt names?
        prefix = self._make_unique(name)

        for key in sorted(signal._prims.keys()):
            prim_name = prefix + ''.join('_%s' % part for part in key)
            self.name_prim(
                signal._prim(key), prim_name, check_signal=False)

        # Intentionally added late to not block the name for a prim with key ()
        self.used_names.add(prefix)

    def name_submodule(self, module, name=None):
        try:
            return self.module_to_name[module]
        except KeyError:
            pass
        # TODO better alt names
        name = self._make_unique(name)
        self.used_names.add(name)
        self.module_to_name[module] = name
        module._module_data.name = name

        subnames = module._module_data.names

        for prim in module._module_data.io_prims:
            self.name_prim(
                prim, '%s_%s' % (name, subnames.name_prim(prim)),
                check_signal=False)

    def name_prim(self, prim, name=None, check_signal=True):
        # TODO has simplify_read always the semantics we want here?
        prim = prim.simplify_read()
        try:
            return self.prim_to_name[prim]
        except KeyError:
            pass

        if check_signal and isinstance(prim, PrimStorage) and prim.signal:
            # TODO will name ever be not None here?
            self.name_signal(prim.signal, name)
            return self.name_prim(prim, name, check_signal=False)

        # TODO better alt names?
        vec_suffixes = tuple(self._make_vec_suffixes(prim.dimensions))
        name = self._make_unique(name, suffixes=vec_suffixes)
        self.used_names.update(name + suffix for suffix in vec_suffixes)
        self.prim_to_name[prim] = name

        return name

    def _make_unique(self, name, alt_name='unk', suffixes=('',)):
        if name is None:
            name = alt_name
        # TODO sanitize name
        if name in _reserved_names:
            name = '_' + name
        if self._is_unique(name, suffixes):
            return name
        for i in count(1):
            attempt = '%s_%i' % (name, i)
            if self._is_unique(attempt, suffixes):
                return attempt

    def _is_unique(self, name, suffixes):
        return all(
            name + suffix not in self.used_names
            for suffix in suffixes)

    @classmethod
    def _make_vec_suffixes(cls, dimensions):
        if dimensions == ():
            yield ''
        else:
            for inner_suffix in cls._make_vec_suffixes(dimensions[1:]):
                for i in range(dimensions[0]):
                    yield '%s_%i' % (inner_suffix, i)
