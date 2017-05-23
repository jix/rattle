from collections import OrderedDict
from pathlib import Path

from ... import context
from ...module import Module
from ...type import Bool, Bits, Bundle, Flip
from ...type.inout import InOut
from ...signal import Input, Output
from ...attribute import DoNotGenerate


_make_port = {
    'I': Input,
    'O': Output,
    'Master': Output,
    'Slave': Input,
}


class BlockDesign(Module):
    def __init__(self, tcl_script_path, force_lowercase=True):
        self.force_lowercase = force_lowercase
        tcl_script_path = Path(tcl_script_path)
        self._tcl_script = tcl_script_path.read_text()

        build = context.current().build

        self._block_design_port_info = (
            build.get_block_design_ports(self._tcl_script))

        self.attribute(DoNotGenerate)
        self._create_ports()

    def _parse_module_ports(self):
        module_ports = OrderedDict()
        module_buses = OrderedDict()

        current_bus = {}

        for line in self._block_design_port_info.split('\n'):
            line = line.split()
            if not line:
                continue

            if line[0] == 'intf':
                intf = line[1][1:]
                intf_mode = line[2]

                current_bus = {}
                module_buses[intf] = intf_mode, current_bus
            elif line[0] == 'port':
                if len(line) > 3:
                    vectors = sorted(map(int, line[3:]))
                    signal_type = Bits(vectors[1] - vectors[0])
                else:
                    signal_type = Bool

                port_name = line[1][1:]
                port_dir = line[2]

                if intf is None:
                    if port_dir == 'IO':
                        port_dir = 'O'
                        signal_type = InOut(signal_type)
                    module_ports[port_name] = port_dir, signal_type
                    continue

                if port_dir == 'IO':
                    signal_type = InOut(signal_type)
                else:
                    if (intf_mode == 'Slave') ^ (port_dir == 'I'):
                        signal_type = Flip(signal_type)

                field_name = port_name[len(intf) + 1:]

                if self.force_lowercase:
                    field_name = field_name.lower()

                current_bus[field_name] = port_name, signal_type
            elif line[0] == 'ports':
                intf = None
                current_bus = None

        return module_ports, module_buses

    def _create_ports(self):
        module_ports, module_buses = self._parse_module_ports()

        for name, (direction, signal_type) in module_ports.items():
            port = _make_port[direction](signal_type)

            self._module_data.names.name_signal(port, name)

            if self.force_lowercase:
                name = name.lower()

            setattr(self, name, port)

        for name, (direction, fields) in module_buses.items():
            signal_type = Bundle(**{k: v[1] for k, v in fields.items()})

            port = _make_port[direction](signal_type)

            for field, (port_name, _signal_type) in fields.items():
                self._module_data.names.name_signal(port[field], port_name)

            if self.force_lowercase:
                name = name.lower()

            setattr(self, name, port)
