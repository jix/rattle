from itertools import chain
from .signal import Const, Value
from .bitvec import BitVec, XClass, bv


class ExprEval:
    def raw_value(self, signal):
        if isinstance(signal, Const):
            return signal.raw_value
        elif isinstance(signal, Value):
            return self.eval_value(signal.expr)
        else:
            return self.provide_raw_value(signal)

    @staticmethod
    def provide_raw_value(signal):
        return None

    def eval_value(self, expr):
        fn = getattr(self, expr.eval_fn_name)
        return fn(*expr)

    def _eval_nop(self, x):
        return self.raw_value(x)

    def _eval_field(self, name, x):
        x = self.raw_value(x)
        if x is None:
            return
        return x[name]

    def _eval_const_index(self, index, x):
        x = self.raw_value(x)
        if x is None:
            return
        res = x[index]
        if isinstance(res, (bool, XClass)):
            res = bv(res)
        return res

    def _eval_dynamic_index(self, index, x):
        index, x = self.raw_value(index), self.raw_value(x)
        if index is None or x is None:
            return

        res = None
        for i in index.values():
            if i >= len(x):
                return self._xval(x[0])
            else:
                res = self._combine(res, x[i])
        assert res is not None
        return res

    def _eval_const_slice(self, start, length, x):
        x = self.raw_value(x)
        if x is None:
            return
        return x[start:start + length]

    def _eval_flip(self, x):
        # pylint: disable=no-self-use
        # TODO Can this happen? Better error message
        raise RuntimeError('Flip in eval')

    def _eval_concat(self, parts):
        # TODO Make sure parts is never created empty
        parts = [self.raw_value(part) for part in parts]
        if any(part is None for part in parts):
            return
        if isinstance(parts[0], BitVec):
            return BitVec.concat(*parts)
        else:
            return tuple(chain(*parts))

    def _eval_not(self, x):
        x = self.raw_value(x)
        if x is None:
            return
        return ~x

    def _eval_and(self, a, b):
        a, b = self.raw_value(a), self.raw_value(b)
        # TODO Short circuit?
        if a is None or b is None:
            return
        return a & b

    def _eval_or(self, a, b):
        a, b = self.raw_value(a), self.raw_value(b)
        # TODO Short circuit?
        if a is None or b is None:
            return
        return a | b

    def _eval_xor(self, a, b):
        a, b = self.raw_value(a), self.raw_value(b)
        # TODO Short circuit?
        if a is None or b is None:
            return
        return a ^ b

    def _eval_add(self, a, b):
        a, b = self.raw_value(a), self.raw_value(b)
        if a is None or b is None:
            return
        return a + b

    def _eval_sub(self, a, b):
        a, b = self.raw_value(a), self.raw_value(b)
        if a is None or b is None:
            return
        return a - b

    def _eval_mul(self, a, b):
        a, b = self.raw_value(a), self.raw_value(b)
        if a is None or b is None:
            return
        return a * b

    def _eval_eq(self, a, b):
        a, b = self.raw_value(a), self.raw_value(b)
        if a is None or b is None:
            return
        return bv(a == b)

    def _eval_sign_ext(self, bits, x):
        x = self.raw_value(x)
        if x is None:
            return
        return BitVec.concat(x, x[-1:].repeat(bits - x.width))

    def _eval_zero_ext(self, bits, x):
        x = self.raw_value(x)
        if x is None:
            return
        return BitVec.concat(x, BitVec(bits - x.width, 0))

    def _eval_repeat(self, count, x):
        x = self.raw_value(x)
        if x is None:
            return
        return x.repeat(count)

    def _eval_bundle(self, fields):
        fields = dict(
            (key, self.raw_value(field)) for key, field in fields.items())
        if any(field is None for field in fields.values()):
            return
        return fields

    def _eval_vec(self, elements):
        elements = tuple(self.raw_value(element) for element in elements)
        if any(element is None for element in elements):
            return
        return elements

    def _xval(self, value):
        if isinstance(value, (bool, XClass)):
            return BitVec(1, 0, -1)
        elif isinstance(value, BitVec):
            return BitVec(value.width, 0, -1)
        elif isinstance(value, (tuple, list)):
            return tuple(self._xval(v) for v in value)
        elif isinstance(value, dict):
            return {k: self._xval(v) for k, v in value.items()}

    def _combine(self, a, b):
        if isinstance(b, (bool, XClass)):
            b = bv(b)
        if a is None:
            return b

        if isinstance(a, BitVec):
            return a.combine(b)
        elif isinstance(a, (tuple, list)):
            return tuple(self._combine(x, y) for x, y in zip(a, b))
        elif isinstance(a, dict):
            return {k: self._combine(x, b[k]) for k, x in a.items()}


const_expr_eval = ExprEval()
