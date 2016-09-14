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
        self.module_colors = [
            '#888888', '#ff0000', '#00ff00', '#0000ff'
        ]

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

    def module_color(self):
        result = self.module_colors[0]
        self.module_colors.append(self.module_colors.pop(0))
        return result


class ModuleToGraph:
    def __init__(
            self, module, depth=1,
            cluster=True, lowered_only=False, node_ids=None):
        if depth == 'all':
            depth = -1
        if node_ids is None:
            node_ids = NodeIds()
        self.ids = node_ids
        self.module = module
        self.lowered_only = lowered_only
        module_data = module._module_data
        if cluster:
            self.graph = graphviz.Digraph('cluster_' + self.ids.unique())
        else:
            self.graph = graphviz.Digraph('subgraph_' + self.ids.unique())

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
            fillcolor='#dddddd',
            fontname='Linux Libertine',
            tooltip=' ',
        )

        if cluster:
            self.graph.attr(
                'node',
                shape='plaintext',
                style='filled',
            )
        else:
            self.graph.attr(
                'node',
                shape='box',
                style='filled',
                color=self.ids.module_color(),
            )
        self.graph.attr(
            'edge',
            fontname='Linux Libertine',
            color='#666666',
            tooltip=' ',
        )

        for signal in module_data.storage_signals:
            if isinstance(signal, IOPort):
                if not (lowered_only and signal._lowered is not None):
                    self.signal(signal)

        if depth == 0:
            return

        for submodule in module_data.submodules:
            submodule_to_dot = ModuleToGraph(
                module=submodule,
                depth=depth - 1,
                cluster=cluster,
                lowered_only=lowered_only,
                node_ids=self.ids)
            self.graph.subgraph(submodule_to_dot.graph)

            for signal in submodule._module_data.storage_signals:
                if isinstance(signal, IOPort):
                    if not (lowered_only and signal._lowered is not None):
                        if signal._lowered is not None:
                            self.add_lowering(signal, signal._lowered[1], True)

        for signal in module_data.storage_signals:
            if not (lowered_only and signal._lowered is not None):
                if signal._lowered is not None:
                    self.add_lowering(signal, signal._lowered[0], False)
                self.signal(signal)

        if not lowered_only:
            for signal in module_data.named_signals:
                self.signal(signal)

        if not lowered_only:
            for i, assignment in enumerate(module_data.assignments):
                self.add_assignment(i, *assignment)

        for i, assignment in enumerate(module_data.lowered_assignments):
            self.add_lowered_assignment(i, *assignment)

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

    def add_lowering(self, signal, lowered_signal, parent):
        signal_id = self.signal(signal)
        lowered_id = self.signal(lowered_signal)

        reverse = isinstance(signal, Output) ^ parent

        if reverse:
            self.graph.edge(
                lowered_id, signal_id,
                style='dashed', arrowtail='diamond', dir='back')
        else:
            self.graph.edge(
                signal_id, lowered_id,
                style='dashed', arrowhead='diamond')

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

    def add_flip(self, *args):
        self.add_commutative('&#8644;', *args)

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

    def add_const_slice(self, signal, start, length, vec):
        expr_node = self.add_signal_node(
            signal, '[%i:[%i]]' % (start, length))
        self.graph.edge(self.signal(vec), expr_node)

    def add_concat(self, signal, parts):
        expr_node = self.add_signal_node(signal, '++')
        for i, element in enumerate(parts):
            element_id = self.ids.unique()
            self.graph.node(element_id, label='#%i' % i)
            self.graph.edge(element_id, expr_node)
            self.graph.edge(self.signal(element), element_id)

    def add_input(self, signal):
        self.add_signal_node(signal, '&#8594;&#9725;', fillcolor='#99ff99')

    def add_output(self, signal):
        self.add_signal_node(signal, '&#9725;&#8594;', fillcolor='#ff9999')

    def add_reg(self, signal):
        reg_node = self.add_signal_node(signal, '&#916;', fillcolor='#ffff99')
        if not self.lowered_only:
            self.graph.edge(
                self.signal(signal.clk),
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

    def add_lowered_assignment(self, i, timing, target, condition, value):
        condition_node = self.ids.unique()
        self.graph.node(condition_node, label=str(i))

        if timing['mode'] == 'initial':
            initial_node = self.ids.unique()
            self.graph.node(
                initial_node, label='initial', fillcolor='#99ffff')
            self.graph.edge(
                initial_node,
                condition_node,
                style='dotted',
            )
        elif timing['mode'] == 'reg':
            self.graph.edge(
                self.signal(timing['clk']),
                condition_node,
                style='dotted',
            )
            if 'reset' in timing:
                self.graph.edge(
                    self.signal(timing['reset']),
                    condition_node,
                    style='dotted',
                )

        color = '#666666' if self.lowered_only else '#0000ff'

        self.graph.edge(
            condition_node, self.signal(target),
            arrowhead='empty',
            color=color)
        self.graph.edge(
            self.signal(value), condition_node,
            arrowhead='none',
            color=color)

        for (polarity, signal) in condition:
            self.graph.edge(
                self.signal(signal), condition_node,
                style='dashed',
                color='#00dd00' if polarity else '#aa0000')
