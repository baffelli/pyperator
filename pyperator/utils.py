import asyncio


# class Edge:
#     def __init__(self, source, dest, outport, inport):
#         self.source = source
#         self.dest = dest
#         self.outport = outport
#         self.inport = inport
#         # self._qu = asyncio.Queue()
#         # self._qu.put_nowait(None)
#
#     # async def send(self, data):
#     #     await self._qu.put(data)
#     #
#     # async def receive(self):
#     #     data = await self._qu.get()
#     #     return data
#
#     def __repr__(self):
#         return "{source}:{outport}-> {dest}:{inport}".format(source=self.source, dest=self.dest,
#                                                              inport=self.inport, outport=self.outport)
#
#     def __eq__(self, other):
#         return (
#             self.source == other.source and self.dest == other.dest and
#             self.inport == other.outport and self.outport == other.outport)
#
#     def __hash__(self):
#         return (self.source, self.dest, self.inport, self.outport).__hash__()


conn_template = "{component}:{name}"




class Port:
    def __init__(self, name, size=1, component=None):
        self.name = name
        self.component = component
        self.other = None
        self.queue = asyncio.Queue()

    def set_initial_value(self, value):
        self.queue.put_nowait(value)

    async def send(self, data):
        await self.other.queue.put(data)

    async def receive(self):
        if self.is_connected:
            data = await self.queue.get()
            return data
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
                await other.queue.put(data)
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
        self.ports = {}

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


    def __repr__(self):
       return "{component}: {ports}".format(component=self.component, ports=list(self.ports.keys()))

    def values(self):
        return self.ports.values()