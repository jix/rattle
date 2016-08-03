import graphviz

from ..signal import *
from ..reg import *


class NodeIds:
    def __init__(self):
        self.counter = 0
        self.mapping = {}

    def __getitem__(self, obj):
        try:
            return self.mapping[obj]
        except KeyError:
            pass
        node_id = self.unique()
        self.mapping[obj] = node_id
        return node_id

    def unique(self):
        node_id = 'n%i' % self.counter
        self.counter += 1
        return node_id


class ModuleToGraph:
    def __init__(self, module, depth=1, node_ids=None):
        if depth == 'all':
            depth = -1
        if node_ids is None:
            node_ids = NodeIds()
        self.ids = node_ids
        self.module = module
        self.graph = graphviz.Digraph('cluster_' + self.ids.unique())
        self.signals = set()

        self.graph.attr(
            'graph',
            color='black', label=repr(module),
            fontname='Linux Libertine',
            rankdir='LR',
            style='dotted',
            ranksep='0.3',
            maxiter='300',
        )
        self.graph.attr(
            'node',
            height='0.01', width='0.01',
            margin='0.04,0.02',
            shape='plaintext',
            style='filled',
            fillcolor='#dddddd',
            fontname='Linux Libertine',
        )
        self.graph.attr(
            'edge',
            fontname='Linux Libertine',
            color='#666666',
        )
        for signal in module._module_data.io_signals:
            self.signal(signal)

        if depth == 0:
            return

        for signal in module._module_data.named_signals:
            self.signal(signal)

        for submodule in module._module_data.submodules:
            submodule_to_dot = ModuleToGraph(
                module=submodule,
                depth=depth - 1,
                node_ids=self.ids)
            self.graph.subgraph(submodule_to_dot.graph)

        for i, assignment in enumerate(module._module_data.assignments):
            self.add_assignment(i, *assignment)

    def signal(self, signal):
        if signal in self.signals:
            return self.ids[signal]
        elif isinstance(signal, Const):
            signal_id = self.ids.unique()
            self.graph.node(
                signal_id, label='%r\n%r' % (signal.value, signal.signal_type),
                fillcolor='#ff99ff')
            return signal_id
        else:
            if isinstance(signal, Input):
                self.add_input(signal)
            elif isinstance(signal, Output):
                self.add_output(signal)
            elif isinstance(signal, Reg):
                self.add_reg(signal)
            elif isinstance(signal, Wire):
                self.add_wire(signal)
            elif isinstance(signal, Value):
                self.add_value(signal)
            else:
                raise RuntimeError('unexpected signal node type')
            self.signals.add(signal)
            return self.ids[signal]

    def add_value(self, signal):
        getattr(self, 'add_' + signal.expr.fn_name)(signal, *signal.expr)

    def add_not(self, *args):
        self.add_commutative('&#172;', *args)

    def add_and(self, *args):
        self.add_commutative('&#8743;', *args)

    def add_or(self, *args):
        self.add_commutative('&#8744;', *args)

    def add_xor(self, *args):
        self.add_commutative('&#8853;', *args)

    def add_nop(self, *args):
        self.add_commutative('&#9251;', *args)

    def add_commutative(self, name, signal, *args):
        expr_node = self.ids[signal]
        self.graph.node(expr_node, label='%s\n%r' % (name, signal.signal_type))
        for arg in args:
            self.graph.edge(self.signal(arg), expr_node)

    def add_input(self, signal):
        self.graph.node(
            self.ids[signal],
            label='&#8594;&#9725;\n%r' % signal.signal_type,
            fillcolor='#99ff99',
        )

    def add_output(self, signal):
        self.graph.node(
            self.ids[signal],
            label='&#9725;&#8594;\n%r' % signal.signal_type,
            fillcolor='#ff9999',
        )

    def add_reg(self, signal):
        self.graph.node(
            self.ids[signal],
            label='&#916;\n%r' % signal.signal_type,
            fillcolor='#ffff99',
        )
        self.graph.edge(
            self.ids[signal.clk],
            self.ids[signal],
            style='dotted',
        )

    def add_wire(self, signal):
        self.graph.node(
            self.ids[signal],
            label='&#8943;\n%r' % signal.signal_type,
            fillcolor='#9999ff',
        )

    def add_assignment(self, i, target, condition, value):
        condition_node = self.ids.unique()
        self.graph.node(condition_node, label=str(i))
        self.graph.edge(
            condition_node, self.ids[target],
            arrowhead='empty')
        self.graph.edge(
            self.signal(value), condition_node,
            arrowhead='none')

        for (polarity, signal) in condition:
            self.graph.edge(
                self.ids[signal], condition_node,
                style='dashed',
                color='#00dd00' if polarity else '#aa0000')
