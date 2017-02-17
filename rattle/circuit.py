from collections import OrderedDict


class Circuit:

    def __init__(self):
        self.combinational = OrderedDict()
        self.assign = OrderedDict()
        self.clocked = OrderedDict()
        self.async_reset = OrderedDict()
        self.sync_reset = OrderedDict()
        self.initial = OrderedDict()

        self.clocked_storage = {}

        self.finalized = False
        # TODO forbid modification after finalizing

    def add_combinational(self, storage, target, condition, source):
        storage = storage.simplify_read()
        try:
            block = self.combinational[storage]
        except KeyError:
            block = self.combinational[storage] = Block()
        block.add_assignment(storage, target, condition, source)

    def add_clocked(self, storage, clock, target, condition, source):
        storage = storage.simplify_read()
        try:
            block = self.clocked[clock]
        except KeyError:
            block = self.clocked[clock] = Block()
        block.add_assignment(storage, target, condition, source)
        self.clocked_storage.setdefault(storage, set()).add(clock)

    def add_sync_reset(self, storage, clock, reset, target, source):
        storage = storage.simplify_read()
        try:
            block = self.sync_reset[clock]
        except KeyError:
            block = self.sync_reset[clock] = Block()
        block.add_assignment(storage, target, ((True, reset),), source)
        self.clocked_storage.setdefault(storage, set()).add(clock)

    def add_async_reset(self, storage, clock, reset, target, source):
        storage = storage.simplify_read()
        try:
            block = self.async_reset[(clock, reset)]
        except KeyError:
            block = self.async_reset[(clock, reset)] = Block()
        block.add_assignment(storage, target, (), source)
        self.clocked_storage.setdefault(storage, set()).add(clock)

    def add_initial(self, storage, target, source):
        storage = storage.simplify_read()
        try:
            block = self.initial[storage]
        except KeyError:
            block = self.initial[storage] = Block()
        block.add_assignment(storage, target, (), source)

    @staticmethod
    def _opt_passes():
        from .opt.lower_sync_reset import LowerSyncReset
        from .opt.find_continuous_assignments import FindContinuousAssignments

        return [
            LowerSyncReset,
            FindContinuousAssignments,
        ]

    def finalize(self):
        if self.finalized:
            return

        for opt_pass in self._opt_passes():
            opt_pass(self)

        self.finalized = True

    def __repr__(self):
        lines = []
        lines.append('Circuit %s' % hex(id(self)))
        for storage, block in self.combinational.items():
            lines.append('combinational for %r:' % storage)
            lines.extend(block._repr_lines(indent='  '))
        for clock, block in self.clocked.items():
            lines.append('clocked for %r:' % clock)
            lines.extend(block._repr_lines(indent='  '))
        for clock, block in self.sync_reset.items():
            lines.append('sync reset for clock %r:' % clock)
            lines.extend(block._repr_lines(indent='  '))
        for (clock, reset), block in self.async_reset.items():
            lines.append('async reset %r for clock %r:' % (reset, clock))
            lines.extend(block._repr_lines(indent='  '))
        for storage, block in self.async_reset.items():
            lines.append('initial for %r:' % storage)
            lines.extend(block._repr_lines(indent='    '))
        return '\n'.join(lines)


class Block:
    def __init__(self):
        self.assignments = []
        self.storage = set()

    def add_assignment(self, storage, target, condition, source):
        position = self.assignments
        new_condition = ()

        for i, test in enumerate(condition):
            if position and position[-1][:2] == ('?', test[1]):
                position = position[-1][3 - test[0]]
            else:
                new_condition = condition[i:]
                break

        for test in new_condition:
            if_node = ('?', test[1], [], [])
            position.append(if_node)
            position = if_node[3 - test[0]]

        position.append(('=', storage, target, source))
        self.storage.add(storage)

    def __repr__(self):
        return '\n'.join(self._repr_lines())

    def _repr_lines(self, indent=''):
        lines = []

        def recurse(assignments, indent):
            if not assignments:
                lines.append('%spass' % indent)
                return
            for statement in assignments:
                if statement[0] == '=':
                    lines.append('%s%r := %r' % (
                        indent, statement[2], statement[3]))
                elif statement[0] == '?':
                    lines.append('%swhen %r:' % (
                        indent, statement[1]))
                    recurse(statement[2], indent + '  ')
                    lines.append('%selse:' % indent)
                    recurse(statement[3], indent + '  ')
                else:
                    assert False

        recurse(self.assignments, indent)
        return lines
