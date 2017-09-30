from ..visitor import visitor
from ..primitive import *


class VerilogTemplates:
    # pylint: disable=no-self-use
    # pylint: disable=function-redefined
    @visitor
    def _expr_template(self, expr):
        raise RuntimeError('no verilog template for primitive %r' % expr)

    @_expr_template.on(PrimIndex)
    def _expr_template(self, expr):
        x = (expr.x, 'indexable', 0)
        index = (expr.index, 'self', 99)
        return (x, '[', index, ']'), 'indexable', 0

    @_expr_template.on(PrimNot)
    def _expr_template(self, expr):
        x = (expr.x, 'context', 1)
        return ('~', x), 'context', 1

    @_expr_template.on(PrimConcat)
    def _expr_template(self, expr):
        tokens = []
        for part in reversed(expr.parts):
            tokens.append(', ')
            tokens.append((part, 'self', 99))

        tokens[0] = '{'
        tokens.append('}')

        return tokens, 'self', 0

    _op_templates = {
        PrimMul: (' * ', 2),
        PrimAdd: (' + ', 4),
        PrimSub: (' - ', 4),
        PrimShiftLeft: (' << ', 6),
        PrimShiftRight: (' >> ', 6),
        PrimArithShiftRight: (' >>> ', 6),
        PrimLt: (' < ', 8),
        PrimEq: (' == ', 10),
        PrimAnd: (' & ', 12),
        PrimXor: (' ^ ', 14),
        PrimOr: (' | ', 16),
    }

    @_expr_template.on(PrimBinaryOp)
    def _expr_template(self, expr):
        op, prec = self._op_templates[type(expr)]
        return (
            (expr.a, 'context', prec + 1), op, (expr.b, 'context', prec)
        ), 'context', prec + 1

    @_expr_template.on(PrimCompareOp)
    def _expr_template(self, expr):
        op, prec = self._op_templates[type(expr)]
        return (
            (expr.a, 'context', prec + 1), op, (expr.b, 'context', prec)
        ), 'self', prec + 1

    @_expr_template.on(PrimSignedLt)
    def _expr_template(self, expr):
        return (
            '$signed(', (expr.a, 'context', 99),
            ') < $signed(', (expr.b, 'context', 99), ')'
        ), 'self', 7

    @_expr_template.on(PrimShiftOp)
    def _expr_template(self, expr):
        op, prec = self._op_templates[type(expr)]
        return (
            (expr.x, 'context', prec + 1), op, (expr.shift, 'self', prec)
        ), 'context', prec + 1

    @_expr_template.on(PrimSignExt)
    def _expr_template(self, expr):
        return ('$signed(', (expr.x, 'self', 99), ')'), 'assign', 0

    @_expr_template.on(PrimZeroExt)
    def _expr_template(self, expr):
        # TODO inline ext?
        return ((expr.x, 'no-context', 99), ), 'assign', 0

    @_expr_template.on(PrimSlice)
    def _expr_template(self, expr):
        if expr.width == 1:
            slice_str = '[%i]' % expr.start
        else:
            slice_str = '[%i:%i]' % (expr.start + expr.width - 1, expr.start)

        return (
            (expr.x, 'named', 0),
            slice_str
        ), 'self', 0

    @_expr_template.on(PrimRepeat)
    def _expr_template(self, expr):
        return (
            '{%i{' % expr.count,
            (expr.x, 'self', 99),
            '}}'
        ), 'self', 0

    @_expr_template.on(PrimBitIndex)
    def _expr_template(self, expr):
        return (
            (expr.x, 'indexable', 0), '[', (expr.index, 'self', 99), ']'
        ), 'self', 0

    @_expr_template.on(PrimMux)
    def _expr_template(self, expr):
        if expr.index.width != 1:
            tokens = []
            template = ' == %i\'h%%0%ix ? ' % (
                expr.index.width, (expr.index.width + 3) // 4)
            for i, port in enumerate(expr.ports):
                tokens.append((expr.index, 'context', 11))
                tokens.append(template % i)
                tokens.append((port, 'context', 18))
                tokens.append(' : ')

            tokens.append('%i\'b%s' % (
                expr.width, 'x' * expr.width))

            return tokens, 'context', 19
        return (
            (expr.index, 'self', 18), ' ? ',
            (expr.ports[1], 'context', 18), ' : ',
            (expr.ports[0], 'context', 19)
        ), 'context', 19

    @_expr_template.on(PrimConst)
    def _expr_template(self, expr):
        return ('%i\'b%s' % (expr.width, expr.value),), 'const', 0

    @visitor
    def _expr_is_simple(self, expr):
        # pylint: disable=unused-argument
        return False

    @_expr_is_simple.on(PrimStorage)
    def _expr_is_simple(self, expr):
        # pylint: disable=unused-argument
        return True

    @_expr_is_simple.on(PrimIndex)
    def _expr_is_simple(self, expr):
        return (
            isinstance(expr.index, PrimConst) and
            self._expr_is_simple(expr.x))

    @_expr_is_simple.on(PrimNot)
    def _expr_is_simple(self, expr):
        return self._expr_is_simple(expr.x)

    @_expr_is_simple.on(PrimSlice)
    def _expr_is_simple(self, expr):
        return self._expr_is_simple(expr.x)

    @_expr_is_simple.on(PrimConst)
    def _expr_is_simple(self, expr):
        # pylint: disable=unused-argument
        return True

    @visitor
    def _expr_is_inout_port_of(self, expr, port_set):
        # pylint: disable=unused-argument
        return False

    @_expr_is_inout_port_of.on(PrimInOut)
    def _expr_is_inout_port_of(self, expr, port_set):
        return expr.x in port_set

    @_expr_is_inout_port_of.on(PrimIndex)
    def _expr_is_inout_port_of(self, expr, port_set):
        if not isinstance(expr.index, PrimConst):
            return False
        return self._expr_is_inout_port_of(expr.x, port_set)
