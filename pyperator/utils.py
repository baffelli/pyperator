import asyncio


class Connection:
    def __init__(self, source, dest, outport, inport):
        self.source = source
        self.dest = dest
        self.outport = outport
        self.inport = inport
        self._qu = asyncio.Queue()
        self._qu.put_nowait(None)

    async def send(self, data):
        await self._qu.put(data)

    async def receive(self):
        data = await self._qu.get()
        return data

    def __repr__(self):
        return "{source}:{outport}-> {dest}:{inport}".format(source=self.source, dest=self.dest,
                                                             inport=self.inport, outport=self.outport)

    def __eq__(self, other):
        return (
            self.source == other.source and self.dest == other.dest and
            self.inport == other.outport and self.outport == other.outport)

    def __hash__(self):
        return (self.source, self.dest, self.inport, self.outport).__hash__()


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
        if self.other:
            data = await self.queue.get()
            return data
        else:
            return


    def __repr__(self):
        if self.other:
            formatted = "Port {component}:{name} connected to {other.component}:{other.name}".format(**self.__dict__)
        else:
            formatted = ""
        return formatted

    def gv_string(self):
       return conn_template.format(**self.__dict__)


    def connect(self, other_port):
        self.other = other_port
        other_port.other = self


class OutputPort(Port):


    async def receive(self):
        return



class InputPort(Port):

    async def send(self, data):
        return



