import abc
from .bitvec import BitVec, bv
from .bitmath import log2up
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

        if signal.width == 0:
            return PrimConst(BitVec(0, 0))

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

    def lower_and_add_to_circuit(self, condition, rvalue, circuit, reset):
        if self.width == 0:
            return
        lowered_assignments = self.lower_assignment(condition, rvalue)

        for assignment in lowered_assignments:
            storage, lvalue, condition, rvalue = assignment
            if reset:
                if condition != ():
                    # TODO Change exception type
                    raise RuntimeError(
                        "Assignment lvalues must be static for resets")
                storage.add_reset_to_circuit(circuit, lvalue, rvalue)
            else:
                storage.add_to_circuit(circuit, lvalue, condition, rvalue)

    def lower_assignment(self, condition, rvalue):
        if self.width == 0:
            return
        for assignment in self.split_assignment(condition, rvalue):
            sublvalue, subcondition, subrvalue = assignment

            sublvalue, storage = sublvalue.lower_lvalue()
            yield storage, sublvalue, subcondition, subrvalue

    def split_assignment(self, condition, rvalue):
        if self.width == 0:
            return
        rvalue = rvalue.simplify_read()
        if self.dimensions:
            index_width = log2up(self.dimensions[-1])
            for i in range(self.dimensions[-1]):
                index = PrimConst(BitVec(index_width, i))
                yield from PrimIndex(index, self).split_assignment(
                    condition, PrimIndex(index, rvalue))
        else:
            yield from self.split_scalar(condition, rvalue)

    def split_scalar(self, condition, rvalue):
        yield self, condition, rvalue

    def lower_lvalue(self):
        # pylint: disable=no-self-use
        raise RuntimeError(
            'assignment lvalue could not be '
            'translated into simple lvalues')

    def add_to_circuit(self, circuit, lvalue, condition, rvalue):
        raise RuntimeError(
            'primitive signal %r is not a valid storage node' % self)

    def add_reset_to_circuit(self, circuit, lvalue, rvalue):
        # TODO This is not just an internal error, make nice
        raise RuntimeError(
            'primitive signal %r is not a valid storage node for reset' % self)

    def poke_to_sim(self, sim, lvalue, rvalue, xpoke):
        raise RuntimeError(
            'primitive signal %r cannot be written in simulation' % self)

    @abc.abstractproperty
    def accessed_storage(self):
        pass

    @abc.abstractmethod
    def __iter__(self):
        pass

    def map(self, map_fn):
        return self


class PrimStorage(PrimSignal):
    def __init__(self, module, direction, width, dimensions):
        super().__init__(width=width, dimensions=dimensions)
        self.module = module
        self.direction = direction
        self.signal = None

    def __repr__(self):
        try:
            return self._debug_name
        except AttributeError:
            try:
                # TODO Confusing for submodule IO ports
                return self.module._module_data.names.prim_to_name[self]
            except KeyError:
                return '<PrimStorage(%r, %r, %r, %r) at %x>' % (
                    self.module, self.direction, self.width, self.dimensions,
                    id(self))

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
                return frozenset(['simulation'])
        else:
            return frozenset([self.module])

    def lower_lvalue(self):
        return self, self

    def add_to_circuit(self, circuit, lvalue, condition, rvalue):
        if lvalue.width != 0:
            circuit.add_combinational(self, lvalue, condition, rvalue)

    def poke_to_sim(self, sim, lvalue, rvalue, xpoke):
        if lvalue.width != 0:
            sim._poke(self, lvalue, rvalue, xpoke)

    @property
    def accessed_storage(self):
        return frozenset([self])

    def __iter__(self):
        return iter(())


class PrimValue(PrimSignal, metaclass=abc.ABCMeta):
    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.shape == other.shape and self.tuple() == other.tuple()

    def __hash__(self):
        return hash((type(self), self.shape, self.tuple()))

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
        self.clk = clk.simplify_read()
        self.en = en.simplify_read() if en is not None else None
        self.reset = reset.simplify_read() if reset is not None else None
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

    def lower_lvalue(self):
        return self.x, self

    def add_to_circuit(self, circuit, lvalue, condition, rvalue):
        if lvalue.width == 0:
            return

        if self.en is not None:
            condition += ((True, self.en),)
        circuit.add_clocked(self, self.clk, lvalue, condition, rvalue)

    def add_reset_to_circuit(self, circuit, lvalue, rvalue):
        if lvalue.width == 0:
            return

        if self.reset_mode in ('async+init', 'async'):
            circuit.add_async_reset(self, self.clk, self.reset, lvalue, rvalue)
        elif self.reset_mode in ('sync+init', 'sync'):
            circuit.add_sync_reset(self, self.clk, self.reset, lvalue, rvalue)
        if self.reset_mode in ('init', 'sync+init', 'async+init'):
            circuit.add_initial(self, lvalue, rvalue)
        # TODO Should we error if no reset is emitted?

    def poke_to_sim(self, sim, lvalue, rvalue, xpoke):
        if lvalue.width != 0:
            sim._poke(self, lvalue, rvalue, xpoke)

    @property
    def accessed_storage(self):
        return self.x.accessed_storage

    def __iter__(self):
        yield self.x

    def map(self, map_fn):
        return type(self)(
            self.clk, self.en, self.reset, self.reset_mode, map_fn(self.x))


class PrimIndex(PrimValue):
    def __init__(self, index, x):
        index = index.simplify_read()
        assert index.dimensions == ()
        assert index.width == log2up(x.dimensions[-1])
        super().__init__(
            width=x.width,
            dimensions=x.dimensions[:-1])
        self.x = x
        self.index = index

    def tuple(self):
        return (self.index, self.x)

    def simplify(self):
        if isinstance(self.x, PrimTable) and len(self.x.dimensions) == 1:
            return PrimMux(self.index, self.x.table)
        elif isinstance(self.x, PrimIndex) and isinstance(self.x.x, PrimTable):
            inner_index = self.x
            inner_table = inner_index.x
            new_table = PrimTable(
                PrimIndex(self.index, entry) for entry in inner_table.table)
            return PrimIndex(inner_index.index, new_table)
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

    def lower_lvalue(self):
        x, storage = self.x.lower_lvalue()
        return PrimIndex(self.index, x), storage

    @property
    def accessed_storage(self):
        return self.index.accessed_storage | self.x.accessed_storage

    def __iter__(self):
        yield self.index
        yield self.x

    def map(self, map_fn):
        return type(self)(map_fn(self.index), map_fn(self.x))


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

    @property
    def accessed_storage(self):
        return self.x.accessed_storage

    def __iter__(self):
        yield self.x

    def map(self, map_fn):
        return type(self)(map_fn(self.x))


class PrimConcat(PrimValue):
    # TODO Make PrimConcat writable?
    def __init__(self, parts):
        parts = tuple(
            part.simplify_read() for part in parts if part.width != 0)
        assert all(part.dimensions == () for part in parts)
        super().__init__(
            width=sum(part.width for part in parts))
        self.parts = parts

    def tuple(self):
        return self.parts

    def eval(self, values):
        return BitVec.concat(*(values(part) for part in self.parts))

    @property
    def allowed_readers(self):
        readers = AllSet()
        for part in self.parts:
            readers &= part.allowed_readers
        return readers

    @property
    def accessed_storage(self):
        accessed = frozenset()
        for part in self.parts:
            accessed |= part.accessed_storage
        return accessed

    def __iter__(self):
        return iter(self.parts)

    def map(self, map_fn):
        return type(self)([map_fn(part) for part in self.parts])


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

    @property
    def accessed_storage(self):
        return self.a.accessed_storage | self.b.accessed_storage

    def __iter__(self):
        yield self.a
        yield self.b

    def map(self, map_fn):
        return type(self)(map_fn(self.a), map_fn(self.b))


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

    @property
    def accessed_storage(self):
        return self.a.accessed_storage | self.b.accessed_storage

    def __iter__(self):
        yield self.a
        yield self.b

    def map(self, map_fn):
        return type(self)(map_fn(self.a), map_fn(self.b))


class PrimEq(PrimCompareOp):
    def eval(self, values):
        return bv(values(self.a) == values(self.b))


class PrimLt(PrimCompareOp):
    def eval(self, values):
        return bv(values(self.a) < values(self.b))


class PrimSignedLt(PrimCompareOp):
    def eval(self, values):
        return bv(values(self.a).sign_wrap() < values(self.b).sign_wrap())


class PrimShiftOp(PrimValue, metaclass=abc.ABCMeta):
    def __init__(self, x, shift):
        x, shift = x.simplify_read(), shift.simplify_read()
        assert x.dimensions == ()
        assert shift.dimensions == ()

        super().__init__(width=x.width)
        self.x = x
        self.shift = shift

    def tuple(self):
        return (self.x, self.shift)

    @property
    def allowed_readers(self):
        return self.x.allowed_readers & self.shift.allowed_readers

    @property
    def accessed_storage(self):
        return self.x.accessed_storage | self.shift.accessed_storage

    def __iter__(self):
        yield self.x
        yield self.shift

    def map(self, map_fn):
        return type(self)(map_fn(self.x), map_fn(self.shift))


class PrimShiftLeft(PrimShiftOp):
    def eval(self, values):
        res = None
        x = values(self.x)
        for i in values(self.shift).values():
            res = (x << i).combine(res)
        return res


class PrimShiftRight(PrimShiftOp):
    def eval(self, values):
        res = None
        x = values(self.x)
        for i in values(self.shift).values():
            res = (x >> i).combine(res)
        return res


class PrimArithShiftRight(PrimShiftOp):
    def eval(self, values):
        res = None
        x = values(self.x)
        for i in values(self.shift).values():
            res = (x.arith_rshift(i)).combine(res)
        return res


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

    @property
    def accessed_storage(self):
        return self.x.accessed_storage

    def __iter__(self):
        yield self.x

    def map(self, map_fn):
        return type(self)(self.width, map_fn(self.x))


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

    def simplify(self):
        if self.start == 0 and self.width == self.x.width:
            return self.x
        elif isinstance(self.x, PrimSlice):
            return PrimSlice(self.start + self.x.start, self.width, self.x.x)
        else:
            return self

    def simplify_read(self):
        return PrimSlice(self.start, self.width, self.x.simplify_read())

    @property
    def allowed_readers(self):
        return self.x.allowed_readers

    @property
    def allowed_writers(self):
        return self.x.allowed_writers

    @property
    def accessed_storage(self):
        return self.x.accessed_storage

    def lower_lvalue(self):
        x, storage = self.x.lower_lvalue()
        return PrimSlice(self.start, self.width, x), storage

    def __iter__(self):
        yield self.x

    def map(self, map_fn):
        return type(self)(self.start, self.width, map_fn(self.x))


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

    @property
    def accessed_storage(self):
        return self.x.accessed_storage

    def __iter__(self):
        yield self.x

    def map(self, map_fn):
        return type(self)(self.count, map_fn(self.x))


class PrimBitIndex(PrimValue):
    def __init__(self, index, x):
        index = index.simplify_read()
        assert index.dimensions == ()
        assert index.width == log2up(x.width)
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

    @property
    def accessed_storage(self):
        return self.index.accessed_storage | self.x.accessed_storage

    def lower_lvalue(self):
        # TODO Lower dynamic indexing of a slice into offset dynamic indexing
        if isinstance(self.x, PrimSlice):
            return super().lower_lvalue()
        else:
            x, storage = self.x.lower_lvalue()
            return PrimBitIndex(self.index, x), storage

    def __iter__(self):
        yield self.index
        yield self.x

    def map(self, map_fn):
        return type(self)(map_fn(self.index), map_fn(self.x))


class PrimMux(PrimValue):
    def __init__(self, index, ports):
        index = index.simplify_read()
        ports = tuple(ports)
        assert index.dimensions == ()
        assert ports
        assert index.width == log2up(len(ports))
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

    def simplify(self):
        if isinstance(self.index, PrimConst) and self.index.value.mask == 0:
            try:
                return self.ports[self.index.value.value]
            except IndexError:
                return PrimConst(BitVec(self.width, 0, -1))
        else:
            return self

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

    @property
    def accessed_storage(self):
        accessed = frozenset()
        for port in self.ports:
            accessed &= port.accessed_storage
        return accessed

    def split_scalar(self, condition, rvalue):
        for i, port in enumerate(self.ports):
            index = PrimConst(BitVec(self.index.width, i))
            select = PrimEq(self.index, index)
            yield port, condition + ((True, select),), rvalue

    def __iter__(self):
        yield self.index
        yield from iter(self.ports)

    def map(self, map_fn):
        return type(self)(
            map_fn(self.index), [map_fn(port) for port in self.ports])


class PrimTable(PrimValue):
    def __init__(self, table):
        table = tuple(table)
        assert table
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

    @property
    def accessed_storage(self):
        accessed = frozenset()
        for entry in self.table:
            accessed &= entry.accessed_storage
        return accessed

    def __iter__(self):
        return iter(self.table)

    def map(self, map_fn):
        return type(self)([map_fn(entry) for entry in self.table])


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

    @property
    def allowed_writers(self):
        if self.width == 0:
            return AllSet()
        else:
            return frozenset()

    @property
    def accessed_storage(self):
        return frozenset()

    def __iter__(self):
        return iter(())


__all__ = [
    'PrimSignal',
    'PrimStorage',
    'PrimValue',
    'PrimReg',
    'PrimIndex',
    'PrimNot',
    'PrimConcat',
    'PrimBinaryOp',
    'PrimAnd',
    'PrimOr',
    'PrimXor',
    'PrimAdd',
    'PrimSub',
    'PrimMul',
    'PrimCompareOp',
    'PrimEq',
    'PrimLt',
    'PrimSignedLt',
    'PrimShiftOp',
    'PrimShiftLeft',
    'PrimShiftRight',
    'PrimArithShiftRight',
    'PrimExtendOp',
    'PrimSignExt',
    'PrimZeroExt',
    'PrimSlice',
    'PrimRepeat',
    'PrimBitIndex',
    'PrimMux',
    'PrimTable',
    'PrimConst',
]
