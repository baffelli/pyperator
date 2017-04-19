import asyncio
import re as _re
from collections import OrderedDict as _od
from collections import namedtuple as nt

import pyperator.exceptions
from pyperator.exceptions import PortNotExistingError, PortDisconnectedError, OutputOnlyError, InputOnlyError, \
    MultipleConnectionError, PortClosedError, PortAlreadyConnectedError
from . import IP
from .IP import InformationPacket, EndOfStream, FilePacket

conn_template = "{component.name}:{name}"

import logging

# def reAction(s, l, t):
#     try:
#         pt = _re.compile(t[0]).pattern
#     except:
#         pt = ""
#     return pt
#
#
# def escapeAction(s, l, t):
#     return '\\' + t[0]
#
#
# # Define grammar
# # opener and closer
# _pp.ParserElement.setDefaultWhitespaceChars('\n ')
# wc_open = _pp.Literal('{')
# wc_close = _pp.Literal('}')
#
# wc_content = _pp.Word(_pp.alphanums).setParseAction(lambda t: t[0])
# # Path literals to escape
# path_literal = _pp.Literal('/').setParseAction(escapeAction)
# dot_literal = _pp.Literal('.').setParseAction(escapeAction)
# # Separator for regex
# re_sep = _pp.Literal(',').suppress()


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


# wildcard = (wc_open + (wc_content)('wc_name') + _pp.Optional(re_sep + re('re')) + wc_close)
# # Define path and escape, finally join it
# path = _pp.ZeroOrMore(_pp.Word(_pp.alphanums)) ^ _pp.ZeroOrMore(wildcard) ^ _pp.ZeroOrMore(
#     dot_literal) ^ _pp.ZeroOrMore(path_literal)
#
# res = re.searchString('/a{d,*}/c{e,e{3}}.d')
# print(res.asList())


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


def log_schedule(method):
    def inner(instance):
        try:
            instance._log.info('Component {}: Scheduled'.format(instance.name))
        except AttributeError:
            pass
        return method(instance)

    return inner


class Port:
    def __init__(self, name, size=-1, component=None, blocking=False):
        self.name = name
        self.component = component
        self.other = []
        self.queue = asyncio.Queue()
        self.packet_factory = InformationPacket
        self._open = True
        self._iip = False

    def set_initial_packet(self, value):
        self.component._log.debug("Set initial information packet for {} at port {}".format(self.name, self.component))
        packet = self.packet_factory(value, owner=self.component)
        # self.queue.put_nowait(packet)
        self._iip = packet

    def kickstart(self):
        packet = self.packet_factory(None)
        self.queue.put_nowait(packet)
        self.component._log.debug('Component {}: Kickstarting port {}'.format(self.component, self.name))

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
            # other_port.connect(self)
        else:
            raise PortAlreadyConnectedError(self, other_port)

    async def send_packet(self, packet):
        if self.is_connected:
            if self._open:
                if packet.exists:
                    if packet.owner == self.component or packet.owner == None:
                        for other in self.other:
                            self.component._log.debug(
                                "Component {}: sending {} to {}".format(self.component, str(packet), self.name))
                            await other.queue.put(packet)
                    else:
                        error_message = "Component {}: packets {} is not owned by this component, copy it first".format(
                            self.component, str(packet), self.name)
                        self.component._log.error(error_message)
                        raise pyperator.exceptions.PacketOwnedError(error_message)
                else:
                    ex_str = 'Component {}, Port {}: The information packet with path {} does not exist'.format(
                        self.component, self.port, packet.path)
                    self.component._log.error(ex_str)
                    raise pyperator.exceptions.FileNotExistingError(ex_str)
            else:
                raise PortClosedError()
        else:
            ex_str = '{} is not connected'.format(self.name)
            # logging.getLogger('root').error(ex_str)
            raise PortDisconnectedError()

    async def send(self, data):
        if self.is_connected:
            packet = self.packet_factory(data, owner=self.component)
            await self.send_packet(packet)


    async def receive_packet(self):
        if self.is_connected:
            self.component._log.debug("Component {}: receiving at {}".format(self.component, self.name))
            if not self._iip:
                packet = await self.queue.get()
            else:
                packet = self._iip
            logging.getLogger('root').debug(
                "Component {}: received {} from {}".format(self.component, packet, self.name))
            self.queue.task_done()
            if packet.is_eos and self.queue.empty():
                self.component._log.info(
                    "Component {}: stopping because {} was received".format(self.component, packet))
                raise StopAsyncIteration
            else:
                return packet
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
        self._open = False
        self.component._log.debug("Component {}: closing {}".format(self.component, self.name))


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
        return conn_template.format(**self.__dict__)


class FilePort(Port):
    """
    This is a port used in shell commands
    that exchanges FilePackets instead of regular
    InformationPackets
    """

    def __init__(self, name, component=None):
        super(FilePort, self).__init__(name, component=component)
        self._path = None
        self.packet_factory = FilePacket


class OutputPort(Port):

    def __init__(self, *args, **kwargs):
        super(OutputPort, self).__init__(*args, **kwargs)

    async def receive_packet(self):
        raise OutputOnlyError(self)



class InputPort(Port):
    def __init__(self, *args, **kwargs):
        super(InputPort, self).__init__(*args, **kwargs)
        self._n_ohter = 0

    def connect(self, other_port):
        if self._n_ohter == 0:
            super(InputPort, self).connect(other_port)
            self._n_ohter += 1
        else:
            # ext_text = "A {} port only supports one incoming connection".format(type(self))
            # self.component._log.error(ext_text)
            e = MultipleConnectionError(self)
            self.component._log.error(e)
            raise e

    async def send_packet(self, packet):
        raise InputOnlyError(self)


class PortRegister:
    def __init__(self, component):
        self.component = component
        self.ports = _od()

    def add(self, port):
        try:
            port.component = self.component
        except AttributeError:
            raise PortNotExistingError(self.component, port)
        self.ports.update({port.name: port})

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

    async def receive_packets(self):
        futures = {}
        packets = {}
        for p_name, p in self.items():
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
