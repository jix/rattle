import pprint
import graphviz

from ..signal import *
from ..reg import *
from ..conditional import ResetCondition
from .. import hashutil


class NodeIds:
    def __init__(self):
        self.counter = 0
        self.mapping = {}

    def __getitem__(self, obj):
        key = hashutil.HashInstance(obj)
        try:
            return self.mapping[key]
        except KeyError:
            pass
        node_id = self.unique()
        self.mapping[key] = node_id
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
            style='dotted',
            ranksep='0.3',
            maxiter='300',
            tooltip=' ',
        )
        self.graph.attr(
            'node',
            height='0.01', width='0.01',
            margin='0.04,0.02',
            shape='plaintext',
            style='filled',
            fillcolor='#dddddd',
            fontname='Linux Libertine',
            tooltip=' ',
        )
        self.graph.attr(
            'edge',
            fontname='Linux Libertine',
            color='#666666',
            tooltip=' ',
        )

        for signal in module._module_data.named_signals:
            if isinstance(signal, IOPort):
                self.signal(signal)

        if depth == 0:
            return

        for submodule in module._module_data.submodules:
            submodule_to_dot = ModuleToGraph(
                module=submodule,
                depth=depth - 1,
                node_ids=self.ids)
            self.graph.subgraph(submodule_to_dot.graph)

        for signal in module._module_data.named_signals:
            self.signal(signal)

        for i, assignment in enumerate(module._module_data.assignments):
            self.add_assignment(i, *assignment)

    def signal(self, signal):
        key = hashutil.HashInstance(signal)
        if key in self.signals:
            return self.ids[signal]
        elif isinstance(signal, Const):
            return self.add_signal_node(
                signal, pprint.pformat(signal.value, width=40),
                unique=True,
                fillcolor='#ff99ff')
        elif isinstance(signal, ResetCondition):
            signal_id = self.ids.unique()
            self.graph.node(
                signal_id, label='reset', fillcolor='#99ffff')
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
            self.signals.add(key)
            return self.ids[signal]

    def add_signal_node(self, signal, description, unique=False, **kwds):
        if unique:
            expr_node = self.ids.unique()
        else:
            expr_node = self.ids[signal]
        self.graph.node(
            expr_node, label='%s\n%s' % (
                description, signal.signal_type.short_repr()),
            tooltip=repr(signal.signal_type), **kwds)
        return expr_node

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
        expr_node = self.add_signal_node(signal, name)
        for arg in args:
            self.graph.edge(self.signal(arg), expr_node)

    def add_bundle(self, signal, fields):
        expr_node = self.add_signal_node(signal, '{&#8943;}')
        for name, field in fields.items():
            field_id = self.ids.unique()
            self.graph.node(field_id, label='%s=' % name)
            self.graph.edge(field_id, expr_node)
            self.graph.edge(self.signal(field), field_id)

    def add_field(self, signal, name, bundle):
        expr_node = self.add_signal_node(signal, '.%s' % name)
        self.graph.edge(self.signal(bundle), expr_node)

    def add_vec(self, signal, elements):
        expr_node = self.add_signal_node(signal, '[&#8943;]')
        for i, element in enumerate(elements):
            element_id = self.ids.unique()
            self.graph.node(element_id, label='[%i]=' % i)
            self.graph.edge(element_id, expr_node)
            self.graph.edge(self.signal(element), element_id)

    def add_const_index(self, signal, index, vec):
        expr_node = self.add_signal_node(signal, '[%i]' % index)
        self.graph.edge(self.signal(vec), expr_node)

    def add_input(self, signal):
        self.add_signal_node(signal, '&#8594;&#9725;', fillcolor='#99ff99')

    def add_output(self, signal):
        self.add_signal_node(signal, '&#9725;&#8594;', fillcolor='#ff9999')

    def add_reg(self, signal):
        reg_node = self.add_signal_node(signal, '&#916;', fillcolor='#ffff99')
        self.graph.edge(
            self.ids[signal.clk],
            reg_node,
            style='dotted',
        )

    def add_wire(self, signal):
        self.add_signal_node(signal, '&#8943;', fillcolor='#9999ff')

    def add_assignment(self, i, target, priority, condition, value):
        condition_node = self.ids.unique()
        if priority != 0:
            label = '%i:%i' % (priority, i)
        else:
            label = str(i)
        self.graph.node(condition_node, label=label)
        self.graph.edge(
            condition_node, self.signal(target),
            arrowhead='empty')
        self.graph.edge(
            self.signal(value), condition_node,
            arrowhead='none')

        for (polarity, signal) in condition:
            self.graph.edge(
                self.signal(signal), condition_node,
                style='dashed',
                color='#00dd00' if polarity else '#aa0000')
