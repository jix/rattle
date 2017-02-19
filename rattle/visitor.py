# TODO support inheritance for the visiting class?


class Visitor:
    def __init__(self):
        self._handlers = {}

    def on(self, target_type):
        return lambda fn: self._add_handler(target_type, fn)

    def _add_handler(self, target_type, fn):
        self._handlers[target_type] = fn
        return self

    def __get__(self, obj, objtype):
        def dispatch(target, *args, **kwds):
            return self._dispatch(
                type(target).__mro__, obj, target, *args, **kwds)

        def dispatch_super(target_type, target, *args, **kwds):
            return self._dispatch(
                target_type.__mro__[1:], obj, target, *args, **kwds)

        dispatch.super = dispatch_super

        return dispatch

    def _dispatch(self, mro, obj, target, *args, **kwds):
        for target_type in mro:
            handler = self._handlers.get(target_type)
            if handler is not None:
                break
        # This should always terminate due to having a handler for object
        return handler(obj, target, *args, **kwds)


def visitor(fn):
    # TODO be a nicer decorator and copy metadata
    v = Visitor()
    v._add_handler(object, fn)
    return v
