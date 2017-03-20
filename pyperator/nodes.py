from pyperator.utils import messageList, channel
import asyncio




class Port:

    def __init__(self, name, size=1):
        self.name = name
        self._queue = asyncio.Queue(size)

    async def send(self, data):
        await self._queue.put(data)

    async def receive(self):
        data = self._queue.get()
        return data

    def connect(self, other):
        self._queue = other._queue


class Component:
    def __init__(self, name, f=lambda x: None, inputs=[], outputs=[]):
        self.name = name
        #Input and output ports
        self._inports = {}
        self._outports = {}
        #Function of the node
        self._f = f
        self.color = 'grey'
        #initalize ports
        for inport in inputs:
            self._inports.update({inport: Port(inport)})
        for outport in outputs:
            self._outports.update({outport: Port(outport)})

    def __repr__(self):
        st = "{}".format(self.name)
        return st

    def gv_node(self):
        table_header = """<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0"><TR><TD BORDER="0"><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">"""
        st = """
                node[shape=record]
                {name} [fillcolor={c}, label=\"{name}\", style=filled]""".format(c=self.color, name=str(self))
        return st


    def connect(self, other, outport, inport):
        """
        Connection protocol:
        output port is always connect to input port of other node
        """
        #Check if the given port exists in this component
        output_ports = [current_port for outport_name, current_port, in self.outports if outport_name == outport]
        #Check if the given inport exists in the other component
        input_ports = [inport for current_port, inport_name in other.inports if inport_name == inport]
        if output_ports:
            if input_ports:
                output_ports[0].connect(input_ports)


    @property
    def outports(self):
        yield from self._outports.items()

    @property
    def inports(self):
        yield from self._inports.items()


class Node:
    def __init__(self, name, f=lambda x: None):
        #Each node has a name
        self.name = name
        #Nodes are stored as dicts
        self._in = {}
        self._out = {}
        #This is the function that the node will execute
        self.f = f
        self.data = []
        self.color = 'grey'



    def connect(self, other):
        pass

    def __repr__(self):
        st = "{}".format(self.name)
        return st

    def gv_node(self):
        st = "{name} [fillcolor={c}, label=\"{name}\", style=filled]".format(c=self.color, name=str(self))
        return st

    def add_outgoing(self, node):
        if not node in self._out:
            self._out.add(node)

    def add_incoming(self, node):
        # Find channels
        if not node in self._in:
            self._in.add(node)

    def remove_outgoing(self, node):
        self._out.pop(node)

    def remove_incoming(self, node):
        self._in.pop(node)

    def find_channel(self, node):
        c = [c for c in self._channels if c.connection_exists(self, node)] + [c for c in node._channels if
                                                                              c.connection_exists(self, node)]
        return c[0]


    async def get_upstream(self):
        data = []
        if self.n_in > 0:
            for incoming_node  in self.incoming:
                print("{}, receiving on {}".format(self.name, incoming_node))
                current_data = await self.channel.receive()
                self.data.append(current_data)
                return
        return data

    async def send_downstream(self, data):
        if self.n_out > 0:
            for outgoing_node in self.outgoing:
                print("{}, sending {} to {}".format(self.name, data, outgoing_node))
                #send data to the node
                await outgoing_node.channel.send(data)
                print('{} sent data downstream'.format(self.name))
                await outgoing_node()
        return



    async def __call__(self, *args, **kwargs):
            print('executing {}'.format(self.name))
            if self.n_in > 0:
                data = await self.get_upstream()
            else:
                data = None
            print('{} processing data '.format(self.name))
            if len(self.data) == self.n_in:
                if self.n_in ==0:
                    transformed = self.f(data)
                else:
                    transformed = await self.f(self.data)

                transformed = (self.name, transformed)

                print("result {}".format(transformed))
                await self.send_downstream(transformed)
                self.data = []











    @property
    def n_in(self):
        return len(self._in)

    @property
    def n_out(self):
        return len(self._out)

    @property
    def outgoing(self):
        yield from self._out

    @property
    def incoming(self):
        yield from self._in

    @property
    def has_predecessor(self):
        if self._in:
            return True
