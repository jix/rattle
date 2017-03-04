from .engine import SimEngine
from ..bitmath import log2up
from ..bitvec import BitVec
from ..primitive import PrimConst, PrimTable, PrimIndex
from .. import context


class SimContext:
    def __init__(self, module):
        module._module_data.circuit.finalize()

        self._engine = SimEngine(module)

    def activate(self):
        return context.current().activate_sim_context(self)

    def peek(self, signal):
        const_prims = {}

        for key, prim in signal._prims.items():
            const_prims[key] = self._peek_prim(prim.simplify_read())

        return signal.signal_type._from_prims(const_prims)

    def _peek_prim(self, prim):
        if not prim.dimensions:
            return PrimConst(self._engine.peek(prim))
        else:
            size = prim.dimensions[-1]
            index_width = log2up(size)
            return PrimTable([
                self._peek_prim(
                    PrimIndex(PrimConst(BitVec(index_width, i)), prim))
                for i in range(size)])
