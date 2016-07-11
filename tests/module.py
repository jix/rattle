from functools import wraps
from rattle.module import Module


def construct_as_module(fn):
    @wraps(fn)
    def wrapper(*args, **kwds):
        class TestModule(Module):
            def construct(self, *args, **kwds):
                fn(self, *args, **kwds)
        TestModule(*args, **kwds)
    return wrapper
