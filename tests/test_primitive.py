from rattle.primitive import *


def mkvars(names, width=1, dimensions=()):
    results = []
    for name in names.split():
        result = PrimStorage(None, None, width, dimensions)
        result._debug_name = name
        results.append(result)
    if len(results) == 1:
        return results[0]
    else:
        return results


def test_index_table_to_mux_simple():
    a, b, index = mkvars('a b index')
    expr = PrimIndex(index, PrimTable([a, b]))
    assert expr == PrimMux(index, [a, b])


def test_index_table_to_mux_nested():
    a, b, c, d, i1, i2 = mkvars('a b c d i1 i2')
    t1 = PrimTable([a, b])
    t2 = PrimTable([c, d])
    expr = PrimIndex(i1, PrimIndex(i2, PrimTable([t1, t2])))
    assert expr == PrimMux(i2, [PrimMux(i1, [a, b]), PrimMux(i1, [c, d])])


def test_index_table_to_mux_nested_mixed():
    a, b, i1, i2 = mkvars('a b i1 i2')
    t1 = PrimTable([a, b])
    t2 = mkvars('t2', dimensions=(2,))
    expr = PrimIndex(i1, PrimIndex(i2, PrimTable([t1, t2])))
    assert expr == PrimMux(i2, [PrimMux(i1, [a, b]), PrimIndex(i1, t2)])


def test_lower_vector_to_scalars():
    a, b = mkvars('a b', dimensions=(4,))
    c = mkvars('c')

    def index(v):
        return PrimConst(BitVec(2, v))

    lowered = list(a.lower_assignment(((True, c),), b))
    assert lowered == [
        (a, PrimIndex(index(0), a), ((True, c),), PrimIndex(index(0), b)),
        (a, PrimIndex(index(1), a), ((True, c),), PrimIndex(index(1), b)),
        (a, PrimIndex(index(2), a), ((True, c),), PrimIndex(index(2), b)),
        (a, PrimIndex(index(3), a), ((True, c),), PrimIndex(index(3), b)),
    ]


def test_lower_mux_target_to_conditional_assigns():
    a, b, c, d, e = mkvars('a b c d e')

    lowered = list(PrimMux(a, [b, c]).lower_assignment(((True, e),), d))

    assert lowered == [
        (b, b, ((True, e), (True, PrimEq(a, PrimConst(bv('0'))))), d),
        (c, c, ((True, e), (True, PrimEq(a, PrimConst(bv('1'))))), d),
    ]
