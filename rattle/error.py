class NoModuleUnderConstruction(RuntimeError):
    pass


class InvalidSignalAccess(RuntimeError):
    pass


class InvalidSignalAssignment(InvalidSignalAccess):
    pass


class InvalidSignalRead(InvalidSignalAccess):
    pass


class ConversionNotImplemented(NotImplementedError):
    pass


class ImplicitNotFound(RuntimeError):
    pass
