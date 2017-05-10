import asyncio
from abc import ABCMeta, abstractmethod

from pyperator import IP
from pyperator.utils import PortRegister
import pyperator.logging as _log
import pyperator.context


class AbstractComponent(metaclass=ABCMeta):
    """
    This is an abstract component
    """

    @abstractmethod
    def __call__(self):
        pass

    @abstractmethod
    def iternodes(self):
        yield self


class Component(AbstractComponent):
    def __init__(self, name):
        self.name = name
        # Input and output ports
        self.inputs = PortRegister(self)
        self.outputs = PortRegister(self)
        # Color of the node
        self.color = 'grey'
        # This is an horrible
        # way to ad a component to
        # the global dag defined whitin
        # a context manager
        self.dag = pyperator.context._global_dag or None
        if self.dag:
            self.dag.add_node(self)
        #The component has a number
        #of owned packets
        self._owned_packets = set()


    def register_packet(self, packet):
        if packet.owner is None:
            packet.owner = self
        self._owned_packets.add(packet)

    def deregister_packet(self, packet):
        if packet in self._owned_packets:
            self._owned_packets.remove(packet)

    @property
    def n_owned_packets(self):
        return len(self._owned_packets)

    def __repr__(self):
        st = "{}".format(self.name)
        return st

    def __str__(self):
        st = "{}".format(self.name)
        return st

    def type_str(self):
        return type(self).__name__


    @property
    def log(self):
        if self.dag:
            return self.dag.log.getChild(self.name)
        else:
            return _log.setup_custom_logger('buttavia')


    def port_table(self):

        def port_element(**kwargs):
            return "<TD PORT=\"{id}\" BGCOLOR=\"{portcolor}\" ALIGN=\"CENTER\">{portname}</TD>".format(
                **kwargs)

        def colspan(nports, ntotal):
            return 1 + (ntotal - nports)

        def map_type(port):
            return 'green' if type(port) is FilePort else 'white'

        def format_ports(ports, total_ports):
            return "".join(
                port_element(id=id(port), portname=port.name, portcolor=map_type(port),
                             colspan=colspan(len(list(ports)), len(list(total_ports)))) for port in ports)

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

        return table_template.format(color=self.color, comp_name=self.name, type_str=self.type_str(), inports=inports,
                                     outports=outports,
                                     inrow=inrow,
                                     outrow=outrow, colspan=(self.n_in + self.n_out))

    def gv_node(self):
        st = """node[shape=box]
            {name} [label={lab}]""".format(c=self.color, name=id(self), lab=self.port_table())
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
            futures.append(asyncio.ensure_future(p.close()))
        await asyncio.wait(futures)

    def send_to_all(self, data):
        # Send
        self.log.debug("Sending '{}' to all output ports".format(data))
        packets = {p: IP.InformationPacket(data, owner=self) for p, v in self.outputs.items()}
        futures = self.outputs.send_packets(packets)
        return futures

    async def active(self):
        self.color = 'green'

    async def inactive(self):
        self.color = 'grey'

    def __lshift__(self, port):
        """
        Adds an :class:`pyperator.utils.port` to the component inputs.
        Equivalent to :code:`self.inputs.add(port)`

        :param port: :class:`pyperator.utils.port`
        :return: :class:`pyperator.nodes.Component`
        """
        self.inputs.add(port)
        return self

    def __rshift__(self, port):
        """
        Adds an :class:`pyperator.utils.port` to the component outputs.
        Equivalent to :code:`self.outputs.add(port)`

        :param port: :class:`pyperator.utils.port`
        :return: :class:`pyperator.nodes.Component`
        """
        self.outputs.add(port)
        return self

    async def __call__(self):
        pass

    def iternodes(self):
        yield self



    @property
    def n_in(self):
        return len(self.inputs)

    @property
    def n_out(self):
        return len(self.outputs)

    @property
    def successors(self):
        yield from (port._connection.dest for port_name, port in self._outports.items())
