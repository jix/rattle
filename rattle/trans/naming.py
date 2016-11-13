from ..hashutil import hash_key
from ..signal import IOPort
from ..type.vec import Vec


class Naming:
    def __init__(self, module):
        self.module = module
        self.signal_names = {}
        self.used_names = set()

        module_data = module._module_data

        for named in (True, False):
            for io_ports in (True, False):
                for signal in module_data.storage_signals:
                    if (isinstance(signal, IOPort) == io_ports and
                            (signal._named is not None) == named):
                        self._name_with_lowereds(signal, io_port=io_ports)

    def _name_with_lowereds(self, signal, io_port=False):
        suffixes = {}

        if signal._lowered is None:
            lowered_parts = {(): signal}
        else:
            lowered_parts = signal._lowered_parts

        for path in sorted(lowered_parts.keys()):
            part_signal = lowered_parts[path]
            if io_port:
                vec_suffixes = list(
                    self._vec_suffixes(part_signal.signal_type))
            else:
                vec_suffixes = ['']

            suffix = ''.join('_' + el for el in path)

            current = suffix
            counter = 1
            while any(current + v in suffixes for v in vec_suffixes):
                counter += 1
                current = '%s%i' % (suffix, counter)

            suffix = current
            suffixes[suffix] = part_signal

            for vec_suffix in vec_suffixes:
                if vec_suffix != '':
                    suffixes[suffix + vec_suffix] = None

        base_name = self._suggested_name(signal)

        current = base_name
        counter = 1
        while any(current + s in self.used_names for s in suffixes):
            counter += 1
            current = '%s%i' % (base_name, counter)

        base_name = current

        for suffix, suffix_signal in suffixes.items():
            name = base_name + suffix
            self.used_names.add(name)
            if suffix_signal is not None:
                self.signal_names[hash_key(suffix_signal)] = name

    def _vec_suffixes(self, signal_type):
        if not isinstance(signal_type, Vec):
            yield ''
        else:
            for i in range(signal_type.length):
                for sub_suffix in self._vec_suffixes(signal_type.element_type):
                    yield '_%i%s' % (i, sub_suffix)

    def _suggested_name(self, signal):
        if signal._named is not None:
            return signal._named
        key = hash_key(signal)
        try:
            return self.module._module_data.automatic_names[key]
        except KeyError:
            return 'zzunk'

    def name(self, signal):
        key = hash_key(signal)
        try:
            return self.signal_names[key]
        except KeyError:
            name = self._suggested_name(signal)

            current = name
            counter = 1
            while current in self.used_names:
                counter += 1
                current = '%s%i' % (name, counter)

            name = current

            self.signal_names[key] = name
            return name
