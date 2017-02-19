# pylint: disable=attribute-defined-outside-init, no-self-use,
# pylint: disable=function-redefined
from rattle.visitor import visitor


class R:
    pass


class AR(R):
    pass


class BR(R):
    pass


class AAR(AR):
    pass


class AAAR(AAR):
    pass


def test_visitor_default_method():
    class V:
        @visitor
        def visit(self, obj):
            self.obj = obj

    v = V()
    v.visit('foo')
    assert v.obj == 'foo'


def test_visitor_flat_hierarchy():
    class V:
        @visitor
        def visit(self, obj):
            raise RuntimeError('no handler')

        @visit.on(R)
        def visit(self, obj):
            self.obj = 'r', obj

        @visit.on(AR)
        def visit(self, obj):
            self.obj = 'ar', obj

        @visit.on(BR)
        def visit(self, obj):
            self.obj = 'br', obj

    r, ar, br = R(), AR(), BR()

    v = V()
    v.visit(r)
    assert v.obj == ('r', r)

    v = V()
    v.visit(ar)
    assert v.obj == ('ar', ar)

    v = V()
    v.visit(br)
    assert v.obj == ('br', br)


def test_visitor_mro():
    class V:
        @visitor
        def visit(self, obj):
            raise RuntimeError('no handler')

        @visit.on(R)
        def visit(self, obj):
            self.obj = 'r', obj

        @visit.on(AR)
        def visit(self, obj):
            self.obj = 'ar', obj

        @visit.on(BR)
        def visit(self, obj):
            self.obj = 'br', obj

    r, ar, aar, aaar = R(), AR(), AAR(), AAAR()

    v = V()
    v.visit(r)
    assert v.obj == ('r', r)

    v = V()
    v.visit(ar)
    assert v.obj == ('ar', ar)

    v = V()
    v.visit(aar)
    assert v.obj == ('ar', aar)

    v = V()
    v.visit(aaar)
    assert v.obj == ('ar', aaar)


def test_visitor_super():
    class V:
        @visitor
        def visit(self, obj):
            raise RuntimeError('no handler')

        @visit.on(R)
        def visit(self, obj):
            self.obj = 'r', obj

        @visit.on(AAR)
        def visit(self, obj):
            self.aar = True
            self.visit.super(AAR, obj)

        @visit.on(AAAR)
        def visit(self, obj):
            self.obj = 'aaar', obj

    r, ar, aar, aaar = R(), AR(), AAR(), AAAR()

    v = V()
    v.visit(r)
    assert v.obj == ('r', r)

    v = V()
    v.visit(ar)
    assert v.obj == ('r', ar)

    v = V()
    v.visit(aar)
    assert v.obj == ('r', aar)
    assert v.aar

    v = V()
    v.visit(aaar)
    assert v.obj == ('aaar', aaar)
