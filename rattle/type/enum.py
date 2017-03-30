from collections import OrderedDict
import re

from .type import SignalType
from .bits import Bits
from .bool import Bool
from ..signal import Signal
from ..conditional import when
from ..bitvec import BitVec, X, XClass
from ..bitmath import log2up, bitmask


class Enum(SignalType):
    def __init__(self, *states):
        parsed_states = []
        seen_states = set()

        if not states:
            raise ValueError('empty Enum declaration')

        for state in states:
            parsed = self._parse_state(state)
            if parsed[0] in seen_states:
                raise ValueError(
                    'duplicate state %r in Enum declaration' % parsed[0])
            seen_states.add(parsed[0])
            parsed_states.append(parsed)

        self._states = self._build_encoding(parsed_states)

        first_state = next(iter(self._states.values()))

        self._state_width = first_state.state_value.width
        self._data_width = first_state.data_value.width

        if not all(
                state.state_value.width == self._state_width
                for state in self._states.values()):
            raise ValueError('different state encoding lengths')

        if not all(
                state.data_value.width == self._data_width
                for state in self._states.values()):
            raise ValueError('different data encoding lengths')

    @property
    def _signature_tuple(self):
        return (type(self), tuple(self._states.items()))

    @property
    def _signal_class(self):
        return EnumSignal

    @property
    def _prim_shape(self):
        return {
            (): (False, self._state_width),
            ('data',): (False, self._data_width)}

    def _unpack(self, unpacker):
        state_prim = unpacker.unpack(self._state_width)._prim()
        data_prim = unpacker.unpack(self._data_width)._prim()

        return self._from_prims({(): state_prim, ('data',): data_prim})

    def _parse_state(self, state):
        if isinstance(state, str):
            return [state, None, None, {}]
        elif not isinstance(state, (tuple, list)):
            raise TypeError('%r is not a valid Enum state declaration' % state)

        orig_state = state

        name, *state = state

        field_types = {}

        if state and isinstance(state[-1], dict):
            *state, field_types = state
            field_types = dict(field_types)
            for field_type in field_types.values():
                if field_type.contains_flipped:
                    raise TypeError(
                        'Enum cannot contain bidirectional type %r' %
                        field_type)

        state_pattern = None
        data_pattern = None

        used_fields = set()

        if state:
            state_pattern = self._parse_pattern(
                state[0], field_types, used_fields, data_pattern=False)
            if len(state) > 1:
                data_pattern = self._parse_pattern(
                    state[1], field_types, used_fields, data_pattern=True)

                unused_fields = field_types.keys() - used_fields
                if unused_fields:
                    raise ValueError(
                        'unused fields %r in enum state declaration' %
                        tuple(sorted(unused_fields)))
            if len(state) > 2:
                raise ValueError(
                    'enum state declaration %r has unexpected extra elements' %
                    orig_state)

        for field in used_fields:
            del field_types[field]

        return [name, state_pattern, data_pattern, field_types]

    @staticmethod
    def _parse_pattern(pattern, field_types, used_fields, data_pattern):
        if pattern is None:
            return None
        if not isinstance(pattern, str):
            raise TypeError('Enum state pattern has to be a string')

        bitpos = 0
        data = 0
        data_xval = 0
        mask = 0
        fields = {}

        for token in reversed(re.findall(r'\{[^}]*\}|\S', pattern)):
            char = token[0]
            if char in '01+-x':
                data |= (char in '1+') << bitpos
                data_xval |= (char == 'x') << bitpos
                mask |= (char in '01') << bitpos

                bitpos += 1
            elif char == '{':
                field_name = token[1:-1].strip()
                if field_name in used_fields:
                    raise KeyError(
                        'field %r already used in Enum state declaration' %
                        field_name)
                try:
                    field_type = field_types[field_name]
                except KeyError:
                    raise KeyError(
                        'no field %r specified in Enum state declaration' %
                        field_name)
                field_width = field_type[X].packed.width

                used_fields.add(field_name)
                fields[field_name] = (
                    data_pattern, bitpos, field_width, field_type)

                bitpos += field_width

        return (BitVec(bitpos, data, data_xval), mask, fields)

    @classmethod
    def _build_encoding(cls, states):
        state_missing = any(state[1] is None for state in states)
        state_present = any(state[1] is not None for state in states)
        if state_present and state_missing:
            raise ValueError(
                'specify all or no Enum state patterns')
        data_missing = any(state[2] is None for state in states)
        data_present = any(state[2] is not None for state in states)
        if data_present and data_missing:
            raise ValueError(
                'specify all or no Enum data patterns')

        if state_missing:
            cls._build_state_patterns(states)

        if data_missing:
            cls._build_data_patterns(states)

        return OrderedDict(((
            state[0], EnumStateEncoding(
                state[1][0], state[1][1], state[2][0],
                {**state[1][2], **state[2][2]})) for state in states))

    @staticmethod
    def _build_state_patterns(states):
        width = log2up(len(states))
        mask = bitmask(width)

        for i, state in enumerate(states):
            state[1] = (BitVec(width, i), mask, {})

    @staticmethod
    def _build_data_patterns(states):
        width = max(
            sum(
                field_type[X].packed.width
                for field_type in state[3].values())
            for state in states)

        for state in states:
            field_names = sorted(state[3].keys())
            fields = {}
            bitpos = 0

            for field_name in field_names:
                field_type = state[3][field_name]
                field_width = field_type[X].packed.width
                fields[field_name] = (1, bitpos, field_width, field_type)

                bitpos += field_width

            state[2] = (BitVec(width, 0), 0, fields)
            state[3] = {}

    def __repr__(self):
        parts = []

        for state_name, state_encoding in self._states.items():
            state_pattern, data_pattern = state_encoding._repr_patterns()

            parts.append('(%r, %r, %r, %r)' % (
                state_name, state_pattern, data_pattern, {
                    name: signal_type
                    for (name, (*_, signal_type))
                    in state_encoding.fields.items()}))

        return 'Enum(%s)' % ', '.join(parts)

    def _const_signal(self, value, *, implicit):
        # pylint: disable=no-self-use, unused-variable
        # TODO accept EnumState values too
        if isinstance(value, (str, EnumState)):
            value = (value, {})

        if (
                isinstance(value, (tuple, list)) and len(value) == 2 and
                isinstance(value[0], (str, EnumState))):
            state, fields = value
            if isinstance(state, EnumState):
                if state._enum_type != self:
                    raise ValueError('non-matching Enum type')
                state = state._state

            try:
                encoding = self._states[state]
            except KeyError:
                raise ValueError('Enum type has no state %r' % state)
            return encoding.build(self, fields)

        return super()._const_signal(value, implicit=implicit)

    def state(self, state):
        if state not in self._states:
            raise KeyError('Enum type has no state %r' % state)

        return EnumState(self, state)

    def __getattr__(self, name):
        try:
            return self.state(name)
        except KeyError:
            raise AttributeError('Enum type has no attribute %r' % name)


class EnumState:
    def __init__(self, enum_type, state):
        self._enum_type, self._state = enum_type, state

    def __eq__(self, other):
        if not isinstance(other, EnumState):
            return NotImplemented
        return (
            self._enum_type == other._enum_type and
            self._state == other._state)

    def __hash__(self):
        return hash((type(self), self._enum_type, self._state))

    def __repr__(self):
        return self._state

    def __call__(self, *args, **fields):
        if len(args) == 1 and not fields:
            fields = args[0]
        elif args:
            raise TypeError(
                'EnumState takes one positional or only keyword arguments')
        return self._enum_type[self._state, fields]


class EnumStateEncoding:
    def __init__(self, state_value, state_mask, data_value, fields):
        self.state_value = state_value
        self.state_mask = state_mask
        self.data_value = data_value
        self.fields = OrderedDict(sorted(fields.items(), key=lambda x: x[0]))

        assert self.state_value.mask & self.state_mask == 0

    def _tuple(self):
        return (
            self.state_value.width, self.data_value.width,
            self.state_value.value, self.data_value.value,
            self.state_value.mask, self.data_value.mask,
            self.state_mask, self.fields.items())

    def __eq__(self, other):
        if not isinstance(other, EnumStateEncoding):
            return NotImplemented
        return self._tuple() == other._tuple()

    def __hash__(self):
        return hash((type(self), self._tuple()))

    def matches(self, signal):
        return Bits._prim(signal._prim()) & self.state_mask == (
            self.state_value.value & self.state_mask)

    def extract_field(self, signal, state, key):
        try:
            part, start, width, signal_type = self.fields[key]
        except KeyError:
            raise KeyError('Enum state %r has no field %r' % (state, key))

        state = Bits._prim(signal._prim())
        data = Bits._prim(signal._prim(('data',)))

        return signal_type.unpack([state, data][part][start:[width]])

    def build(self, signal_type, fields):
        field_lists = [[], []]

        for name, (part, start, width, field_type) in self.fields.items():
            field_lists[part].append((start, width, name, field_type))

        bits = []
        values = [self.state_value, self.data_value]

        for field_list, value in zip(field_lists, values):
            value = Bits[value]
            parts = []
            field_list.sort(key=lambda field: field[0])

            bitpos = 0

            while bitpos < value.width:
                try:
                    start, width, name, field_type = field_list.pop(0)
                except IndexError:
                    parts.append(value[bitpos:])
                    break
                else:
                    if start != bitpos:
                        parts.append(value[bitpos:start])
                    try:
                        parts.append(field_type[fields[name]].packed)
                    except KeyError:
                        raise KeyError('missing Enum field %r' % name)
                    bitpos = start + width

            bits.append(Bits.concat(*parts))

        return signal_type._from_prims(
            {(): bits[0]._prim(), ('data',): bits[1]._prim()})

    def _repr_patterns(self):
        state_pattern = []

        for i, value in enumerate(self.state_value):
            if self.state_mask & (1 << i):
                state_pattern.append('01'[value])
            elif isinstance(value, XClass):
                state_pattern.append('x')
            else:
                state_pattern.append('-+'[value])

        data_pattern = list(reversed(str(self.data_value)))

        for name, (part, start, width, _field_type) in self.fields.items():
            pattern = data_pattern if part else state_pattern
            if width == 0:
                pattern[start] += '{%s}' % name
            else:
                pattern[start:start+width] = [''] * width
                pattern[start] = '{%s}' % name

        return ''.join(state_pattern[::-1]), ''.join(data_pattern[::-1])


class EnumSelector:
    def __init__(self, signal, state, encoding):
        self._signal = signal
        self._state = state
        self._encoding = encoding
        self._when_context = None

    def _const_signal(self, signal_type, *, implicit):
        if signal_type == Bool:
            return self._signal.in_state(self._state)
        else:
            return NotImplemented

    def __getitem__(self, key):
        return self._encoding.extract_field(self._signal, self._state, key)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError('Enum selector has no attribute %r' % name)

    def __enter__(self):
        self._when_context = when(self)
        self._when_context.__enter__()
        return self

    def __exit__(self, *exc):
        result = self._when_context.__exit__(*exc)
        self._when_context = None
        return result


class EnumSignal(Signal):
    @property
    def value(self):
        state_prim = self._prim_value()
        data_prim = self._prim_value(('data',))

        self.signal_type._from_prims({
            (): state_prim,
            ('data',): data_prim})

    def _add_to_trace(self, trace, scope, name):
        # TODO proper tracing
        trace._add_prim(scope, name, self.packed._prim())

    def _pack(self, packer):
        state = Bits._prim(self._prim())
        data = Bits._prim(self._prim(('data',)))
        packer.pack(state)
        packer.pack(data)

    def in_state(self, state):
        if isinstance(state, EnumState):
            if state._enum_type != self.signal_type:
                raise ValueError('non-matching Enum type')
            state = state._state

        try:
            state_encoding = self.signal_type._states[state]
        except KeyError:
            raise KeyError('Enum type has no state %r' % state)

        return state_encoding.matches(self)

    def __eq__(self, other):
        if isinstance(other, (str, EnumState)):
            return self.in_state(other)
        else:
            return super().__eq__(other)

    @property
    def valid_state(self):
        # TODO detect whether invalid states exist at all
        result = Bool[False]

        for encoding in self.signal_type._states.values():
            result |= encoding.matches(self)

        return result

    def selector(self, state):
        try:
            state_encoding = self.signal_type._states[state]
        except KeyError:
            raise KeyError('Enum type has no state %r' % state)

        return EnumSelector(self, state, state_encoding)

    def __getattr__(self, name):
        try:
            return self.selector(name)
        except KeyError:
            raise AttributeError('Enum signal has no attribute %r' % name)
