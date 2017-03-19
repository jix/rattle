class Trace:
    def __init__(self):
        self._traces = []

    def _add_prim(self, scope, name, prim):
        self._traces.append((scope, name, prim.simplify_read()))
