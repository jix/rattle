from ..circuit import BlockAssign, BlockCond


class RemoveOverwrittenAssignments:
    def __init__(self, circuit):
        for block in circuit.blocks():
            block.assignments, _overwrites = self._process_assignments(
                block.assignments)

    def _process_assignments(self, assignments, overwrites=()):
        overwrites = set(overwrites)

        new_assignments = []

        for statement in reversed(assignments):
            if isinstance(statement, BlockAssign):
                if statement.lvalue not in overwrites:
                    new_assignments.append(statement)
                    overwrites.add(statement.lvalue)
            elif isinstance(statement, BlockCond):
                true, true_overwrites = self._process_assignments(
                    statement.true, overwrites)
                false, false_overwrites = self._process_assignments(
                    statement.false, overwrites)

                if true or false:
                    new_assignments.append(
                        BlockCond(statement.condition, true, false))

                overwrites.update(true_overwrites & false_overwrites)
            else:
                new_assignments.append(statement)

        return new_assignments[::-1], overwrites
