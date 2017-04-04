import asyncio
from collections import OrderedDict as _od

from .IP import  InformationPacket, EndOfStream, FilePacket



conn_template = "{component}:{name}"


class PortNotExistingException(Exception):
    pass


class Port:
    def __init__(self, name, size=1, component=None):
        self.name = name
        self.component = component
        self.other = None
        self.queue = asyncio.Queue()

    def set_initial_packet(self, value):
        packet = InformationPacket(value)
        packet.owner = self.component
        self.queue.put_nowait(packet)

    async def receive(self):
        packet = await self.receive_packet()
        value = packet.value
        packet.drop()
        return value

    async def send(self, value):
        await self.send_packet(value)

    async def send_packet(self, data):
        packet = InformationPacket(data)
        packet.owner = self.component
        await self.other.queue.put(packet)

    async def close(self):
        packet = EndOfStream()
        await self.other.queue.put(packet)

    async def done(self):
        self.other.queue.join()


    @property
    def path(self):
        return None

    @path.setter
    def path(self, path):
        pass


    async def receive_packet(self):
        if self.is_connected:
            packet = await self.queue.get()
            self.queue.task_done()
            if packet.is_eos:
                raise StopIteration
            else:
                return packet
        else:
            return


    @property
    def is_connected(self):
        if self.other is not None:
            return True
        else:
            return False

    def __repr__(self):
        port_template ="Port {component}:{name}"
        if self.other:
            formatted = port_template.format(**self.__dict__)
        else:
            formatted = port_template.format(**self.__dict__) + ', disconnected'
        return formatted

    def gv_string(self):
       return conn_template.format(**self.__dict__)


    def connect(self, other_port):
        self.other = other_port
        connect_dict ={self:other_port}
        if not self.other:
            other_port.connect(self)

    @property
    def connect_dict(self):
        return {self:self.other}

    def iterends(self):
        yield self.other


class FilePort(Port):
    """
    This is a port used in shell commands
    that exchanges FilePackets instead of regular
    InformationPackets
    """

    def __init__(self, name, component=None):
        super(FilePort, self).__init__(name, component=component)
        self._path = None

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path


    async def send_packet(self, data):
        packet = FilePacket(self.path, mode='rw+')
        packet.owner = self.component
        await self.other.queue.put(packet)




class ArrayPort(Port):

    def  __init__(self, name, size=1, component=None):
        super(ArrayPort, self).__init__(name, size=size, component=component)
        self.other = []




    @property
    def connect_dict(self):
        return {self:[other for other in self.other]}

    def iterends(self):
        yield from self.other

    def connect(self, other_port):
        if other_port not in self.other:
            self.other.append(other_port)
            other_port.connect(self)

    async def send(self, data):
        if self.is_connected:
            for other in self.other:
                packet = InformationPacket(data)
                packet.owner = self.component
                await other.queue.put(packet)
        else:
            return



class OutputPort(ArrayPort):

    async def receive(self):
        return


class InputPort(ArrayPort):

    async def send(self, data):
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