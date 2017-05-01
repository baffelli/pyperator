import asyncio
import logging
import re as _re
from collections import OrderedDict as _od
from collections import namedtuple as nt

import pyperator.exceptions
from pyperator.IP import InformationPacket, EndOfStream
from pyperator.exceptions import PortNotExistingError, PortDisconnectedError, OutputOnlyError, InputOnlyError, \
    PortClosedError, PortAlreadyConnectedError, PortAlreadyExistingError

# Constraint for regex (from snakemake)
regex_wildcards = _re.compile(
    r"""
    \{
        (?=(
            \s*(?P<wc_name>\w+)
            (\s*,\s*
                (?P<wc_re>
                    ([^{}]+ | \{\d+(,\d+)?\})*
                )
            )?\s*
        ))\1
    \}
    """, _re.VERBOSE)


class Wildcards(object):
    def __init__(self, pattern):
        self.pattern = pattern

    def get_wildcards(self):
        wc = ()
        constaints = {}
        for a in regex_wildcards.finditer(self.pattern):
            wc_name = a.group('wc_name')
            wc += (wc_name,)
            constaints[wc_name] = a.group('wc_re') or '.+'
        return wc, constaints

    def replace_constraints(self):
        def constraint_replacer(match):
            return '{{{wc}}}'.format(wc=match.group('wc_name'))

        replaced = _re.sub(regex_wildcards, constraint_replacer, self.pattern)
        return replaced

    def parse(self, string):
        wildcards, constraints = self.get_wildcards()
        search_dic = {wc: "(?P<{wc}>{constraint})".format(wc=wc, constraint=constraint) for wc, constraint in
                      constraints.items()}
        path_without_constraints = self.replace_constraints().replace('.', '\.')  # escape dots
        res = _re.compile(path_without_constraints.format(**search_dic)).search(string)
        wc_dic = {}
        for wc_name, wc_value in res.groupdict().items():
            wc_dic[wc_name] = wc_value
        wc_nt = nt('wc', wc_dic.keys())(**wc_dic)
        return wc_nt


class Default(dict):
    """
    from
    "https://docs.python.org/3/library/stdtypes.html#str.format_map"
    """

    def __missing__(self, key):
        return key


class Port:
    """
    This is a regular Port component, that can be connected to another port
    in the same or in another component. It offers methods to send and receive values and packets.
    The port can be configured to have an unlimited capacity or it can be bounded. In the second case,
    sending will when  the connection capacity is reached.
    
    ============================
    Handling several connections
    ============================
    
    If several ports are connected to this
    port simultaneously, they will all send packets to it in a unordered manner and the port
    will not be able to distinguish from which component the packets are 
    being sent (see `noflo`_ ).
    
    For output ports, if several port are connected to the same source, the packets will be replicated
    to all sinks.
    
    .. _noflo: https://github.com/noflo/noflo/issues/90
    """

    def __init__(self, name, size=-1, component=None, mandatory=False):
        self.name = name
        self.size = size
        self.component = component
        self.other = []
        self.queue = asyncio.Queue(maxsize=size)
        self.open = True
        self._iip = False
        #if set to true, the port must be connected
        #before the component can be used
        self.mandatory=mandatory


    @property
    def log(self):
        if self.component:
            return self.component.log.getChild(self.name)


    def set_initial_packet(self, value):
        packet = InformationPacket(value, owner=self.component)
        self._iip = packet

    def kickstart(self):
        packet = InformationPacket(None)
        self.queue.put_nowait(packet)
        self.log.debug('Kickstarting port {}'.format(self.component, self.name))

    async def receive(self):
        packet = await self.receive_packet()
        value = packet.value
        packet.drop()
        return value

    @property
    def connect_dict(self):
        return {self: [other for other in self.other]}

    def iterends(self):
        yield from self.other

    def __rshift__(self, other):
        """
        Nicer form of connect, used
        to connect two ports as
        :code:`a >> b`, equivalent to :code:`a.connect(b)`

        :param other: :class:`pyperator.utils.port`
        :return: None
        """
        self.connect(other)

    def connect(self, other_port):
        if other_port not in self.other:
            self.other.append(other_port)
        else:
            raise PortAlreadyConnectedError(self, other_port)

    async def send_packet(self, packet):
        if self.is_connected:
            if packet.owner == self.component or packet.owner == None:
                for other in self.other:
                    if other.open:
                        self.log.debug(
                            "Sending {} to {}".format(str(packet), self.name))
                        await other.queue.put(packet)
                    else:
                        raise PortClosedError()
            else:
                error_message = "Packet {} is not owned by this component, copy it first".format(str(packet), self.name)
                e = pyperator.exceptions.PacketOwnedError(error_message)
                self.log.ex(e)
                raise e
        else:
            ex_str = '{} is not connected, output packet will be dropped'.format(self.name)
            packet.drop()
            self.log.error(ex_str)
            # raise PortDisconnectedError()

    async def send(self, data):
        packet = InformationPacket(data, owner=self.component)
        await self.send_packet(packet)

    async def receive_packet(self):
        if self.is_connected:
            if self.open:
                self.log.debug("Receiving at {}".format(self.name))
                if not self._iip:
                    packet = await self.queue.get()
                    self.queue.task_done()
                else:
                    packet = self._iip
                    self.log.debug("Receiving IIP at {}".format(self.name))
                    # self.open = False
                self.log.debug(
                    "Received {} from {}".format(packet, self.name))
                if packet.is_eos and self.queue.empty():
                    stop_message = "Stopping because {} was received".format(packet)
                    self.log.info(stop_message)
                    raise StopAsyncIteration(stop_message)
                else:
                    return packet
            else:
                return EndOfStream()
        else:
            raise PortDisconnectedError

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            packet = await self.receive_packet()
            return packet
        except:
            raise StopAsyncIteration

    async def __aenter__(self):
        await asyncio.sleep(0)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        packet = EndOfStream()
        packet.owner = self.component
        await self.send_packet(packet)
        self.open = False
        self.log.debug("Closing {}".format(self.name))

    @property
    def path(self):
        return None

    @path.setter
    def path(self, path):
        pass

    @property
    def is_connected(self):
        if self.other is not []:
            return True
        else:
            return False

    def __repr__(self):
        port_template = "Port {component.name}:{name}"
        formatted = port_template.format(**self.__dict__)
        return formatted

    def gv_string(self):
        return "{compid}:{portid}".format(compid=id(self.component), portid=id(self))

    def gv_conn(self):
        if self.other:
            return "\n".join(
                ["{self} -> {ohter}".format(self=self.gv_string(), ohter=other.gv_string()) for other in self.other])


class FilePort(Port):
    """
    This is a port used in shell commands
    that exchanges FilePackets instead of regular
    InformationPackets
    """

    def __init__(self, *args, **kwargs):
        super(FilePort, self).__init__(*args, **kwargs)


class OutputPort(Port):
    def __init__(self, *args, **kwargs):
        super(OutputPort, self).__init__(*args, **kwargs)

    async def receive_packet(self):
        raise OutputOnlyError(self)

    async def close(self):
        packet = EndOfStream()
        packet.owner = self.component
        await self.send_packet(packet)
        self._open = False
        self.log.debug("Closing {}".format(self.name))


class InputPort(Port):
    def __init__(self, *args, **kwargs):
        super(InputPort, self).__init__(*args, **kwargs)

    async def send_packet(self, packet):
        raise InputOnlyError(self)

    async def close(self):
        self._open = False
        self.log.debug("closing {}".format(self.name))


class ArrayPort(Port):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class PortRegister:
    def __init__(self, component):
        self.component = component
        self.ports = _od()

    def add(self, port):
        self.add_as(port, port.name)

    def add_as(self, port, name):
        if port.component:
            raise PortAlreadyExistingError(self.component, port)
        else:
            try:
                port.component = self.component
            except AttributeError:
                raise PortNotExistingError(self.component, port)
            self.ports.update({name: port})

    def export(self, port, name):
        self.ports.update({name: port})

    def __getitem__(self, item):
        if item in self.ports:
            return self.ports.get(item)
        else:
            raise PortNotExistingError(self.component, str(item))

    def __getattr__(self, item):
        return self[item]

    def __iter__(self):
        return self.ports.__iter__()

    def __len__(self):
        return self.ports.__len__()

    def __str__(self):
        return "{component}: {ports}".format(component=self.component, ports=list(self.ports.keys()))

    # def __repr__(self):
    #     return self.port.__repr__()

    def items(self):
        yield from self.ports.items()

    def values(self):
        return self.ports.values()

    def keys(self):
        return self.ports.keys()

    def iip_iter(self):
        """
        Returns a generator of tuples
        (port, IIP) for all the ports
        that have an Initial Information packet set.
        :return:
        """
        for (port_name, port) in self.items():
            if port._iip:
                yield (port, port._iip.value)

    async def receive_packets(self):
        futures = {}
        packets = {}
        for p_name, p in self.items():
            if p.open:
                futures[p_name] = asyncio.ensure_future(p.receive_packet())
        for k, v in futures.items():
            data = await v
            packets[k] = data
        return packets

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            packets = await self.receive_packets()
            return packets
        except StopAsyncIteration as e:
            raise StopAsyncIteration

    def send_packets(self, packets):
        futures = []
        for p_name, p in self.items():
            packet = packets.get(p_name)
            futures.append(asyncio.ensure_future(p.send_packet(packet)))
        return futures

    def iter_disconnected(self):
        for name, p in self.items():
            if not p.is_connected:
                yield (name, p)

