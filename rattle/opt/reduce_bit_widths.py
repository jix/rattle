from ..visitor import visitor
from ..primitive import *


class ReduceBitWidths:
    # pylint: disable=function-redefined
    def __init__(self, circuit):
        self._required_width = {}

        for prim in circuit.rvalues():
            self._needs_width(prim, prim.width)

        self._changed_width = {}

        self._cache = {}

        circuit.map_rvalues(self._reduce_widths)

    def _needs_width(self, rvalue, width):
        try:
            if self._required_width[rvalue] >= width:
                return
        except KeyError:
            pass
        self._required_width[rvalue] = width
        self._update_subexpr_width(rvalue, width)

    @visitor
    def _update_subexpr_width(self, rvalue, width):
        for subexpr in rvalue:
            self._needs_width(subexpr, subexpr.width)

    @_update_subexpr_width.on(PrimNot)
    def _update_subexpr_width(self, rvalue, width):
        self._needs_width(rvalue.x, width)

    # TODO PrimConcat

    @_update_subexpr_width.on(PrimBinaryOp)
    def _update_subexpr_width(self, rvalue, width):
        self._needs_width(rvalue.a, width)
        self._needs_width(rvalue.b, width)

    @_update_subexpr_width.on(PrimExtendOp)
    def _update_subexpr_width(self, rvalue, width):
        self._needs_width(rvalue.x, min(width, rvalue.x.width))

    @_update_subexpr_width.on(PrimSlice)
    def _update_subexpr_width(self, rvalue, width):
        self._needs_width(rvalue.x, rvalue.start + width)

    # TODO PrimMux

    def _reduce_widths(self, rvalue):
        try:
            return self._cache[rvalue]
        except KeyError:
            pass

        new_width = self._required_width[rvalue]

        new_rvalue = self._reduce_subexpr_width(rvalue, new_width)

        self._cache[rvalue] = new_rvalue
        return new_rvalue

    @visitor
    def _reduce_subexpr_width(self, rvalue, new_width):
        mapped = rvalue.map(self._reduce_widths)
        if new_width != rvalue.width:
            return PrimSlice(0, new_width, mapped)
        else:
            return mapped

    @_reduce_subexpr_width.on(PrimNot)
    def _reduce_subexpr_width(self, rvalue, new_width):
        return type(rvalue)(
            PrimSlice(0, new_width, self._reduce_widths(rvalue.x)))

    @_reduce_subexpr_width.on(PrimBinaryOp)
    def _reduce_subexpr_width(self, rvalue, new_width):
        return type(rvalue)(
            PrimSlice(0, new_width, self._reduce_widths(rvalue.a)),
            PrimSlice(0, new_width, self._reduce_widths(rvalue.b)))

    @_reduce_subexpr_width.on(PrimExtendOp)
    def _reduce_subexpr_width(self, rvalue, new_width):
        if new_width <= rvalue.x.width:
            return PrimSlice(0, new_width, self._reduce_widths(rvalue.x))
        else:
            return type(rvalue)(new_width, self._reduce_widths(rvalue.x))

    @_reduce_subexpr_width.on(PrimSlice)
    def _reduce_subexpr_width(self, rvalue, new_width):
        return type(rvalue)(
            rvalue.start, new_width, self._reduce_widths(rvalue.x))
