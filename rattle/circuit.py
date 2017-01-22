from collections import OrderedDict


class Circuit:
    def __init__(self):
        self.combinational = OrderedDict()
        self.clocked = OrderedDict()
        self.async_reset = OrderedDict()
        self.sync_reset = OrderedDict()
        self.initial = OrderedDict()

    def add_combinational(self, storage, target, condition, source):
        try:
            block = self.combinational[storage]
        except KeyError:
            block = self.combinational[storage] = Block()
        block.add_assignment(target, condition, source)

    def add_clocked(self, clock, target, condition, source):
        try:
            block = self.clocked[clock]
        except KeyError:
            block = self.clocked[clock] = Block()
        block.add_assignment(target, condition, source)

    def add_sync_reset(self, clock, reset, target, source):
        by_clock = self.sync_reset.setdefault(clock, OrderedDict())
        try:
            block = by_clock[reset]
        except KeyError:
            block = by_clock[reset] = Block()
        block.add_assignment(target, (), source)

    def add_async_reset(self, storage, reset, target, source):
        by_storage = self.async_reset.setdefault(storage, OrderedDict())
        try:
            block = by_storage[reset]
        except KeyError:
            block = by_storage[reset] = Block()
        block.add_assignment(target, (), source)

    def add_initial(self, storage, target, source):
        try:
            block = self.initial[storage]
        except KeyError:
            block = self.initial[storage] = Block()
        block.add_assignment(target, (), source)

    def __repr__(self):
        lines = []
        lines.append('Circuit %s' % hex(id(self)))
        for storage, block in self.combinational.items():
            lines.append('combinational for %r:' % storage)
            lines.extend(block._repr_lines(indent='  '))
        for clock, block in self.clocked.items():
            lines.append('clocked for %r:' % clock)
            lines.extend(block._repr_lines(indent='  '))
        for clock, resets in self.sync_reset.items():
            lines.append('sync reset for clock %r:' % clock)
            for reset, block in resets.items():
                lines.append('  reset %r:' % reset)
                lines.extend(block._repr_lines(indent='    '))
        for storage, resets in self.async_reset.items():
            lines.append('async reset for %r:' % storage)
            for reset, block in resets.items():
                lines.append('  reset %r:' % reset)
                lines.extend(block._repr_lines(indent='    '))
        for storage, block in self.async_reset.items():
            lines.append('initial for %r:' % storage)
            lines.extend(block._repr_lines(indent='    '))
        return '\n'.join(lines)


class Block:
    def __init__(self):
        self.assignments = []

    def add_assignment(self, target, condition, source):
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

        position.append(('=', target, source))

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
                        indent, statement[1], statement[2]))
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
