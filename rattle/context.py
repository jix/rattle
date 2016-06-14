import threading
from contextlib import contextmanager

from .error import NoModuleUnderConstruction

_thread_local = threading.local()


class Context:
    def __init__(self):
        self.__module = None

    @property
    def module(self):
        if self.__module is None:
            raise NoModuleUnderConstruction()
        return self.__module

    @contextmanager
    def constructing_module(self, module):
        old_module = self.__module
        self.__module = module
        try:
            yield
        finally:
            self.__module = old_module


def current():
    try:
        return _thread_local.context
    except AttributeError:
        _thread_local.context = rv = Context()
        return rv
