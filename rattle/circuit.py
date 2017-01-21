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
