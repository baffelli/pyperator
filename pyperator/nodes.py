import asyncio
from abc import ABCMeta, abstractmethod

from . import IP
from .utils import PortRegister, FilePort


class AbstractComponent(metaclass=ABCMeta):
    """
    This is an abstract component
    """

    @abstractmethod
    def __call__(self):
        pass


class Component(AbstractComponent):

    def __init__(self, name):
        self.name = name
        # Input and output ports
        self.inputs = PortRegister(self)
        self.outputs = PortRegister(self)
        # Color of the node
        self.color = 'grey'
        self._log = None

    def __repr__(self):
        st = "{}".format(self.name)
        return st

    def __str__(self):
        st = "{}".format(self.name)
        return st

    def type_str(self):
        return type(self).__name__


    def port_table(self):

        def port_element(**kwargs):
            return "<TD PORT=\"{portname}\" BGCOLOR=\"{portcolor}\" ALIGN=\"CENTER\">{portname}</TD>".format(
                **kwargs)

        def colspan(nports, ntotal):
            return 1 + (ntotal - nports)

        def map_type(port):
            return 'green' if type(port) is FilePort else 'white'

        def format_ports(ports, total_ports):
            return "".join(
                port_element(portname=port.name, portcolor=map_type(port), colspan=colspan(len(ports), len(total_ports))) for port in ports)



        row_template = "<TR>{ports}</TR>"

        all_ports = list(self.inputs.values()) + list(self.outputs.values())
        inports = format_ports(self.inputs.values(), all_ports)
        outports = format_ports(self.outputs.values(), all_ports)
        inrow = row_template.format(ports=inports) if len(inports) > 0 else ""
        outrow = row_template.format(ports=outports) if len(outports) > 0 else ""
        table_template = """<
                <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">
                        {inrow}
                        <TR><TD VALIGN="MIDDLE" COLSPAN="{colspan}" BGCOLOR="{color}" ROWSPAN="2" ALIGN="CENTER">{comp_name}<BR/>{type_str}</TD></TR>
                        <TR><TD BORDER="0"></TD></TR>
                        {outrow}
                </TABLE>>"""

        return table_template.format(color=self.color, comp_name=self.name, type_str=self.type_str(), inports=inports, outports=outports,
                                     inrow=inrow,
                                     outrow=outrow, colspan=(self.n_in + self.n_out))

    def gv_node(self):
        st = """node[shape=box]
            {name} [label={lab}]""".format(c=self.color, name=self.name, lab=self.port_table())
        return st

    async def receive(self):
        packets = await self.receive_packets()
        return {k: v.value for k, v in packets.items()}

    async def receive_packets(self):
        packets = await self.inputs.receive_packets()
        for p in packets.values():
            if p.is_eos:
                raise StopAsyncIteration
        return packets

    def send_packets(self, packets):
        return self.outputs.send_packets(packets)

    async def close_downstream(self):
        futures = []
        for p_name, p in self.outputs.items():
            self._log.debug("Component {}: closing downstream {}".format(self.name, p_name))
            futures.append(asyncio.ensure_future(p.close()))
        await asyncio.wait(futures)

    def send_to_all(self, data):
        # Send
        self._log.debug("Component {}: sending '{}' to all output ports".format(self.name, data))
        packets = {p: IP.InformationPacket(data, owner=self) for p, v in self.outputs.items()}
        futures = self.outputs.send_packets(packets)
        return futures

    async def dot(self, ):
        return self.gv_node()

    async def active(self):
        self.color = 'green'

    async def inactive(self):
        self.color = 'grey'

    async def __call__(self):
        pass

    @property
    def n_in(self):
        return len(self.inputs)

    @property
    def n_out(self):
        return len(self.outputs)

    @property
    def successors(self):
        yield from (port._connection.dest for port_name, port in self._outports.items())
