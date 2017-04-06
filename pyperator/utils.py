import asyncio
from collections import OrderedDict as _od

import pyparsing as _pp

from .IP import InformationPacket, EndOfStream, FilePacket

from . import IP

import re as _re

conn_template = "{component}:{name}"


import logging


#Define grammar
#opener and closer
wc_open = _pp.Literal('{')
wc_close = _pp.Literal('}')
wc_content = _pp.Word(_pp.alphanums)('wc')
#Separator for regex
re_sep = _pp.Literal(',')
re = _pp.SkipTo(wc_close)('re')
wildcard = wc_open + (wc_content + _pp.Optional(re_sep)) + re
wildcards = _pp.OneOrMore(wildcard)

class Wildcards(object):
    def __init__(self, pattern):
        self.pattern = pattern
        #Transform the pattern in a
        #dict
        group_dict = {}
        #Transform the pattern into a regex
        for a in wildcard.searchString(pattern):
            #default regex to match everything
            re_str = a.re if a.re else r'.+'
            group_dict[a.wc] = r"(?P<{a.wc}>{re_str})".format(a=a, re_str=re_str)
        self.search_re =  _re.compile(self.pattern.format(**group_dict))
        #Add it to the dict


    def parse(self, string):
        wc_dic = {}
        res = self.search_re.search(string)
        for wc_name, wc_value in res.groupdict().items():
            wc_dic[wc_name] = wc_value
        self.__dict__.update(wc_dic)





class PortNotExistingException(Exception):
    pass

class StopComputation(StopIteration):
    pass

class PortDisconnectedError(Exception):
    pass


class MultipleConnectionError(Exception):
    pass

class Port:
    def __init__(self, name, size=-1, component=None, blocking=False):
        self.name = name
        self.component = component
        self.other = []
        self.queue = asyncio.Queue()
        self.packet_factory = InformationPacket

    def set_initial_packet(self, value):
        logging.getLogger('root').debug("Set initial message for {} at port {}".format(self.name, self.component))
        packet = InformationPacket(value)
        packet.owner = self.component
        self.queue.put_nowait(packet)

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

    def connect(self, other_port):
        if other_port not in self.other:
            self.other.append(other_port)
            other_port.connect(self)

    async def send_packet(self, packet):
        if self.is_connected:
            if packet.exists:
                for other in self.other:
                    self.component._log.debug("Component {}: sending {} to {}".format(self.component, str(packet), self.name))
                    await other.queue.put(packet)
            else:
                ex_str = 'Component {}, Port {}: The information packet with path {} does not exist'.format(self.component, self.port, packet.path)
                self.component._log.error(ex_str)
                raise IP.FileNotExistingError(ex_str)
        else:
            ex_str = '{} is not connected'.format(self.name)
            # logging.getLogger('root').error(ex_str)
            raise PortDisconnectedError(ex_str)

    async def send(self, data):
        if self.is_connected:
            for other in self.other:
                packet = self.packet_factory(data)
                packet.owner = self.component
                await other.queue.put(packet)
        else:
            return

    async def receive_packet(self):
        if self.is_connected:
            self.component._log.debug("Component {}: receiving at {}".format(self.component, self.name))
            packet = await self.queue.get()
            logging.getLogger('root').debug("Component {}: received {} from {}".format(self.component, packet, self.name))
            self.queue.task_done()
            if packet.is_eos:
                self.component._log.info("Component {}: stopping because {} was received".format(self.component, packet))
                raise StopComputation('Done')
            else:
                return packet

    async def close(self):
        packet = EndOfStream()
        await self.send_packet(packet)


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
        port_template = "Port {component}:{name}"
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

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path





class OutputPort(Port):
    pass
    # async def receive_packet(self, packet):
    #     return


class InputPort(Port):

    def __init__(self, *args, **kwargs):
        super(InputPort, self).__init__(*args, **kwargs)
        self._n_ohter = 0

    def connect(self, other_port):
        if self._n_ohter == 0:
            super(InputPort, self).connect(other_port)
            self._n_ohter +=1
        else:
            ext_text = "A {} port only supports one incoming connection".format(type(self))
            self.component._log.error(ext_text)
            raise MultipleConnectionError(ext_text)

    async def send_packet(self, packet):
        return


class PortRegister:
    def __init__(self, component):
        self.component = component
        self.ports = _od()

    def add(self, port):
        port.component = self.component
        self.ports.update({port.name: port})

    def __getitem__(self, item):
        return self.ports.get(item)

    def __getattr__(self, item):
        if item in self.ports:
            return self.ports.get(item)
        else:
            return 'a'

    def __len__(self):
        return self.ports.__len__()

    def __str__(self):
        return "{component}: {ports}".format(component=self.component, ports=list(self.ports.keys()))

    def __repr__(self):
        return self.port.__repr__()

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

    def send_packets(self, packets):
        futures = []
        for p_name, p in self.items():
            packet = packets.get(p_name)
            futures.append(asyncio.ensure_future(p.send_packet(packet)))
        return futures
