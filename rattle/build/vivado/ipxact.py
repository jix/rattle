from collections import OrderedDict
from lxml import etree

from ...module import Module
from ...type import Bool, Bits, Bundle, Flip
from ...type.inout import InOut
from ...signal import Input, Output
from ...attribute import DoNotGenerate


_nsmap = {
    's': 'http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009',
    'x': 'http://www.xilinx.com',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}

_make_port = {
    'in': Input,
    'out': Output,
}


class IpXactComponent(Module):
    def __init__(self, ipxact_xml, force_lowercase=True):
        self.force_lowercase = force_lowercase

        self.ipxact_description = etree.fromstring(ipxact_xml)

        self.attribute(DoNotGenerate)
        self._create_ports()

    def _create_ports(self):
        module_ports = self._parse_module_ports()
        module_buses = self._parse_module_buses(module_ports)

        for name, (direction, signal_type, default) in module_ports.items():
            if direction == 'inout':
                direction = 'out'
                signal_type = InOut(signal_type)

            port = _make_port[direction](signal_type)

            self._module_data.names.name_signal(port, name)

            if default is not None:
                with self.parent.reopen():
                    port[:] = default

            if self.force_lowercase:
                name = name.lower()

            setattr(self, name, port)

        for name, (direction, signal_type, field_map) in module_buses.items():
            port = _make_port[direction](signal_type)

            for field, (field_name, default) in field_map.items():
                self._module_data.names.name_signal(port[field], field_name)

                if default is not None:
                    with self.parent.reopen():
                        port[field][:] = default

            setattr(self, name, port)

    def _parse_module_ports(self):
        module_ports = OrderedDict()
        ports = self.ipxact_description.xpath(
            '/s:component/s:model/s:ports/s:port',
            namespaces=_nsmap)
        for port in ports:
            enablement = port.xpath(
                's:vendorExtensions/x:portInfo/'
                'x:enablement/x:isEnabled/text()',
                namespaces=_nsmap)

            if 'false' in enablement:
                continue

            name, = port.xpath('s:name/text()', namespaces=_nsmap)
            direction, = port.xpath(
                's:wire/s:direction/text()', namespaces=_nsmap)

            vectors = sorted([int(i) for i in port.xpath(
                's:wire/s:vector/s:left/text() |'
                's:wire/s:vector/s:right/text()',
                namespaces=_nsmap)])

            if len(vectors) not in (0, 2):
                raise RuntimeError('could not parse vector bounds')

            default = port.xpath(
                's:wire/s:driver/s:defaultValue/text()', namespaces=_nsmap)

            if default:
                default = int(default[0])
            else:
                default = None

            if vectors:
                signal_type = Bits(vectors[1] - vectors[0] + 1)
            else:
                signal_type = Bool

            module_ports[name] = direction, signal_type, default

        return module_ports

    def _parse_module_buses(self, module_ports):
        # pylint: disable=too-many-locals
        module_buses = OrderedDict()
        buses = self.ipxact_description.xpath(
            '/s:component/s:busInterfaces/s:busInterface',
            namespaces=_nsmap)
        for bus in buses:
            enablement = bus.xpath(
                's:vendorExtensions/x:busInterfaceInfo/'
                'x:enablement/x:isEnabled/text()',
                namespaces=_nsmap)

            if 'false' in enablement:
                continue

            name, = bus.xpath('s:name/text()', namespaces=_nsmap)

            is_slave = bool(bus.xpath('s:slave', namespaces=_nsmap))

            ports = bus.xpath(
                's:portMaps/s:portMap', namespaces=_nsmap)

            fields = {}
            field_map = {}

            for port in ports:
                logical, = port.xpath(
                    's:logicalPort/s:name/text()', namespaces=_nsmap)
                physical, = port.xpath(
                    's:physicalPort/s:name/text()', namespaces=_nsmap)

                physical_dir, signal_type, default = module_ports[physical]
                del module_ports[physical]

                if physical_dir == 'inout':
                    signal_type = InOut(signal_type)
                else:
                    if is_slave ^ (physical_dir == 'in'):
                        signal_type = Flip(signal_type)

                if self.force_lowercase:
                    logical = logical.lower()

                fields[logical] = signal_type
                field_map[logical] = physical, default

            direction = 'in' if is_slave else 'out'

            if self.force_lowercase:
                name = name.lower()

            module_buses[name] = direction, Bundle(**fields), field_map

        return module_buses
