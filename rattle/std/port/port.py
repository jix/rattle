from rattle.prelude import *
from rattle.type.bundle import BundleSignal
from rattle.error import InvalidSignalAssignment


class Port(Bundle):
    def __init__(self, payload_type):
        super().__init__(payload=payload_type, ready=Flip(Bool), valid=Bool)
        self.__payload_type = payload_type

    def __repr__(self):
        return "Port(%r)" % self.__payload_type

    @property
    def payload_type(self):
        return self.__payload_type

    @property
    def _signal_class(self):
        return PortSignal

    def _initialize_reg_value(self, reg):
        reg.valid[:] = False
        try:
            reg.ready[:] = False
        except InvalidSignalAssignment:
            pass


class PortSignal(BundleSignal):
    def _getitem_raw(self, key):
        try:
            return super()._getitem_raw(key)
        except KeyError:
            try:
                return self.payload._getitem_raw(key)
            except KeyError:
                pass
            raise

    @property
    def active(self):
        return self.valid & self.ready
