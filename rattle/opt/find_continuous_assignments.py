from ..circuit import BlockAssign


class FindContinuousAssignments:
    def __init__(self, circuit):
        # TODO expand this to work on vector storage
        for storage in list(circuit.combinational.keys()):
            if (storage in circuit.clocked_storage
                    or storage in circuit.initial):
                continue
            block = circuit.combinational[storage]
            if len(block.assignments) != 1:
                continue
            assignment = block.assignments[0]
            if not isinstance(assignment, BlockAssign):
                continue
            if assignment.lvalue != storage:
                continue
            del circuit.combinational[storage]
            circuit.assign.setdefault(storage, []).append(
                (assignment.lvalue, assignment.rvalue))
