import abc
from .bitvec import BitVec, bv
from .error import ValueNotAvailable


class AllSet:
    def __and__(self, other):
        return other

    def __rand__(self, other):
        return other

    def __contains__(self, key):
        return True


class PrimMeta(abc.ABCMeta):
    def __call__(cls, *args, **kwds):
        signal = super().__call__(*args, **kwds)
        # TODO Memoize

        if isinstance(signal, PrimConst):
            return signal

        def raise_fn(prim):
            raise ValueNotAvailable

        def value_fn(prim):
            return prim.eval(raise_fn)

        try:
            return PrimConst(signal.eval(value_fn))
        except ValueNotAvailable:
            pass

        return signal.simplify()


class PrimSignal(metaclass=PrimMeta):
    def __init__(self, width, dimensions=()):
        self.width = width
        self.dimensions = tuple(dimensions)

    def eval(self, values):
        # pylint: disable=no-self-use
        raise ValueNotAvailable  # TODO Message

    def simplify(self):
        return self

    def simplify_read(self):
        return self

    @property
    def shape(self):
        return (self.width, *self.dimensions)

    @abc.abstractproperty
    def allowed_readers(self):
        pass

    @abc.abstractproperty
    def allowed_writers(self):
        pass


class PrimStorage(PrimSignal):
    def __init__(self, module, direction, width, dimensions):
        super().__init__(width=width, dimensions=dimensions)
        self.module = module
        self.direction = direction

    def __repr__(self):
        return '<PrimStorage(%r, %r, %r, %r) at %x>' % (
            self.module, self.direction, self.width, self.dimensions, id(self))

    @property
    def allowed_readers(self):
        if self.direction is not None and self.module.parent is not None:
            return frozenset([self.module, self.module.parent])
        else:
            return frozenset([self.module])

    @property
    def allowed_writers(self):
        if self.direction == 'input':
            if self.module.parent is not None:
                return frozenset([self.module.parent])
            else:
                return frozenset()
        else:
            return frozenset([self.module])


class PrimValue(PrimSignal, metaclass=abc.ABCMeta):
    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.tuple() == other.tuple()

    def __hash__(self):
        return hash((type(self), self.tuple()))

    @abc.abstractmethod
    def tuple(self):
        pass

    def __repr__(self):
        return "%s(%s)" % (
            type(self).__name__,
            ','.join(repr(i) for i in self.tuple()))

    @property
    def allowed_writers(self):
        return frozenset()


class PrimReg(PrimValue):
    def __init__(self, clk, en, reset, reset_mode, x):
        assert clk.dimensions == ()
        assert clk.width == 1
        assert en is None or en.dimensions == ()
        assert en is None or en.width == 1
        assert reset is None or reset.dimensions == ()
        assert reset is None or reset.width == 1
        assert isinstance(x, PrimStorage)

        super().__init__(width=x.width, dimensions=x.dimensions)
        self.clk = clk
        self.en = en
        self.reset = reset
        self.reset_mode = reset_mode
        self.x = x

    def tuple(self):
        return (self.clk, self.en, self.reset, self.reset_mode, self.x)

    def simplify_read(self):
        return self.x

    @property
    def allowed_readers(self):
        return self.x.allowed_readers

    @property
    def allowed_writers(self):
        return self.x.allowed_writers


class PrimIndex(PrimValue):
    def __init__(self, index, x):
        index = index.simplify_read()
        assert index.dimensions == ()
        super().__init__(
            width=x.width,
            dimensions=x.dimensions[:-1])
        self.x = x
        self.index = index

    def tuple(self):
        return (self.index, self.x)

    def simplify(self):
        # TODO Deeply nested tables
        if isinstance(self.x, PrimTable) and len(self.x.dimensions) == 1:
            return PrimMux(self.index, self.x.table)
        else:
            return self

    def simplify_read(self):
        return PrimIndex(self.index, self.x.simplify_read())

    @property
    def allowed_readers(self):
        return self.x.allowed_readers & self.index.allowed_readers

    @property
    def allowed_writers(self):
        return self.x.allowed_writers & self.index.allowed_readers


class PrimNot(PrimValue):
    def __init__(self, x):
        x = x.simplify_read()
        assert x.dimensions == ()
        super().__init__(
            width=x.width)
        self.x = x

    def tuple(self):
        return (self.x,)

    def eval(self, values):
        return ~values(self.x)

    @property
    def allowed_readers(self):
        return self.x.allowed_readers


class PrimConcat(PrimValue):
    # TODO Make PrimConcat writable?
    def __init__(self, parts):
        parts = tuple(part.simplify_read() for part in parts)
        assert all(part.dimension == () for part in parts)
        super().__init__(
            width=sum(part.width for part in parts))
        self.parts = parts

    def tuple(self):
        return self.parts

    def eval(self, values):
        return BitVec.concat(values(part) for part in self.parts)

    @property
    def allowed_readers(self):
        return self.x.allowed_readers


class PrimBinaryOp(PrimValue, metaclass=abc.ABCMeta):
    def __init__(self, a, b):
        a, b = a.simplify_read(), b.simplify_read()
        assert a.dimensions == ()
        assert b.dimensions == ()
        assert a.width == b.width

        super().__init__(width=a.width)
        self.a = a
        self.b = b

    def tuple(self):
        return (self.a, self.b)

    @property
    def allowed_readers(self):
        return self.a.allowed_readers & self.b.allowed_readers


class PrimAnd(PrimBinaryOp):
    def eval(self, values):
        return values(self.a) & values(self.b)


class PrimOr(PrimBinaryOp):
    def eval(self, values):
        return values(self.a) | values(self.b)


class PrimXor(PrimBinaryOp):
    def eval(self, values):
        return values(self.a) ^ values(self.b)


class PrimAdd(PrimBinaryOp):
    def eval(self, values):
        return values(self.a) + values(self.b)


class PrimSub(PrimBinaryOp):
    def eval(self, values):
        return values(self.a) - values(self.b)


class PrimMul(PrimBinaryOp):
    def eval(self, values):
        return values(self.a) * values(self.b)


class PrimCompareOp(PrimValue, metaclass=abc.ABCMeta):
    def __init__(self, a, b):
        a, b = a.simplify_read(), b.simplify_read()
        assert a.dimensions == ()
        assert b.dimensions == ()
        assert a.width == b.width

        super().__init__(width=1)
        self.a = a
        self.b = b

    def tuple(self):
        return (self.a, self.b)

    @property
    def allowed_readers(self):
        return self.a.allowed_readers & self.b.allowed_readers


class PrimEq(PrimCompareOp):
    def eval(self, values):
        return bv(values(self.a) == values(self.b))


class PrimLt(PrimCompareOp):
    def eval(self, values):
        return bv(values(self.a) < values(self.b))


class PrimSignedLt(PrimCompareOp):
    def eval(self, values):
        return bv(values(self.a).sign_wrap() < values(self.b).sign_wrap())


class PrimExtendOp(PrimValue, metaclass=abc.ABCMeta):
    def __init__(self, width, x):
        x = x.simplify_read()
        assert width >= x.width
        assert x.dimensions == ()

        super().__init__(width=width)
        self.x = x

    def tuple(self):
        return (self.width, self.x)

    @property
    def allowed_readers(self):
        return self.x.allowed_readers


class PrimSignExt(PrimExtendOp):
    def eval(self, values):
        return values(self.x).sign_extend(self.width)


class PrimZeroExt(PrimExtendOp):
    def eval(self, values):
        return values(self.x).extend(self.width)


class PrimSlice(PrimValue):
    def __init__(self, start, width, x):
        assert start + width <= x.width
        assert x.dimensions == ()

        super().__init__(width=width)
        self.start = start
        self.x = x

    def tuple(self):
        return (self.start, self.width, self.x)

    def eval(self, values):
        return values(self.x)[self.start:self.start + self.width]

    def simplify_read(self):
        return PrimSlice(self.start, self.width, self.x.simplify_read())

    @property
    def allowed_readers(self):
        return self.x.allowed_readers

    @property
    def allowed_writers(self):
        return self.x.allowed_writers


class PrimRepeat(PrimValue):
    def __init__(self, count, x):
        x = x.simplify_read()
        assert x.dimensions == ()

        super().__init__(width=x.width * count)
        self.count = count
        self.x = x

    def tuple(self):
        return (self.count, self.x)

    def eval(self, values):
        return values(self.x).repeat(self.count)

    @property
    def allowed_readers(self):
        return self.x.allowed_readers


class PrimBitIndex(PrimValue):
    def __init__(self, index, x):
        index = index.simplify_read()
        assert index.dimensions == ()
        assert x.dimensions == ()

        super().__init__(width=1)
        self.index = index
        self.x = x

    def tuple(self):
        return (self.index, self.x)

    def eval(self, values):
        return bv(values(self.x)[values(self.index)])

    def simplify_read(self):
        return PrimBitIndex(self.index, self.x.simplify_read())

    @property
    def allowed_readers(self):
        return self.index.allowed_readers & self.x.allowed_readers

    @property
    def allowed_writers(self):
        return self.index.allowed_readers & self.x.allowed_writers


class PrimMux(PrimValue):
    def __init__(self, index, ports):
        index = index.simplify_read()
        ports = tuple(ports)
        assert index.dimensions == ()
        assert len(ports) > 0
        assert all(port.dimensions == () for port in ports)
        assert all(port.width == ports[0].width for port in ports)

        super().__init__(width=ports[0].width)
        self.index = index
        self.ports = ports

    def tuple(self):
        return (self.index, self.ports)

    def eval(self, values):
        index_value = values(self.index)

        res = None
        for i in index_value.values():
            if i >= len(self.ports):
                return BitVec(self.width, 0, -1)
            elif res is None:
                res = values(self.ports[i])
            else:
                res = res.combine(values(self.ports[i]))

        assert res is not None

        return res

    def simplify_read(self):
        return PrimMux(
            self.index, (port.simplify_read() for port in self.ports))

    @property
    def allowed_readers(self):
        readers = self.index.allowed_readers
        for port in self.ports:
            readers &= port.allowed_readers
        return readers

    @property
    def allowed_writers(self):
        writers = self.index.allowed_readers
        for port in self.ports:
            writers &= port.allowed_writers
        return writers


class PrimTable(PrimValue):
    def __init__(self, table):
        table = tuple(table)
        assert len(table) > 0
        assert all(entry.shape == table[0].shape for entry in table)

        super().__init__(
            width=table[0].width,
            dimensions=table[0].dimensions + (len(table),))

        self.table = table

    def tuple(self):
        return self.table

    def simplify_read(self):
        return PrimTable((entry.simplify_read() for entry in self.table))

    @property
    def allowed_readers(self):
        readers = AllSet()
        for entry in self.table:
            readers &= entry.allowed_readers
        return readers

    @property
    def allowed_writers(self):
        writers = AllSet()
        for entry in self.table:
            writers &= entry.allowed_writers
        return writers


class PrimConst(PrimValue):
    def __init__(self, value):
        assert isinstance(value, BitVec)
        super().__init__(
            width=value.width)
        self.value = value

    def tuple(self):
        return (self.value.value, self.value.mask)

    def eval(self, values):
        return self.value

    def __repr__(self):
        return 'PrimConst(%s)' % self.value

    @property
    def allowed_readers(self):
        return AllSet()
