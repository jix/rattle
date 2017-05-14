from ...attribute import ModuleName
from ... import context
from .ipxact import IpXactComponent


class IpCore(IpXactComponent):
    def __init__(self, vlnv, config=(), force_lowercase=True):
        build = context.current().build
        escape = build.tcl_escape

        core_name = vlnv.split(':')[2]
        self.attribute(ModuleName(core_name))

        script_parts = [
            'create_ip -vlnv %s -module_name $ipcore_name' % escape(vlnv)]

        for prop, value in config:
            script_parts.append(
                'set_property %s %s [get_ips $ipcore_name]' %
                (escape('CONFIG.%s' % prop), escape(value)))

        self._ipcore_script = '\n'.join(script_parts)

        ipcore_xml = build.get_ipcore_xml(self._ipcore_script)

        super().__init__(ipcore_xml, force_lowercase=force_lowercase)
