from .type import *


class Vec(SignalType):
    def __init__(self, element_type, length):
        super().__init__()
        self.__element_type = element_type
        self.__length = length

    @property
    def element_type(self):
        return self.__element_type

    @property
    def length(self):
        return self.__length

    def __repr__(self):
        return "Vec(%r, %i)" % (self.element_type, self.length)

    @property
    def _signature_tuple(self):
        return (type(self), self.element_type, self.length)
