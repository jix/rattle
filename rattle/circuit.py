class Circuit:
    def __init__(self):
        self.combinational = {}
        self.clocked = {}
        self.async_reset = {}
        self.sync_reset = {}
        self.initial = {}

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
        by_clock = self.sync_reset.setdefault(clock, {})
        try:
            block = by_clock[reset]
        except KeyError:
            block = by_clock[reset] = Block()
        block.add_assignment(target, (), source)

    def add_async_reset(self, storage, reset, target, source):
        by_storage = self.async_reset.setdefault(storage, {})
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
        # TODO Recover / optimize nesting
        self.assignments.append((target, condition, source))
