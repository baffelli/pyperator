from .utils import Connection
from .utils import Port

class Component:
    def __init__(self, name, f=lambda x: None, inputs=[], outputs=[]):
        self.name = name
        # Input and output ports
        self._inports = {}
        self._outports = {}
        # Function of the node
        self.color = 'grey'
        # initalize ports
        for inport in inputs:
            self._inports.update({inport: Port(inport)})
        for outport in outputs:
            self._outports.update({outport: Port(outport)})

    def __repr__(self):
        st = "{}".format(self.name)
        return st

    def port_table(self):

        port_template = "<TD PORT=\"{portname}\">{portname}</TD>"
        row_template = "<TR>{ports}</TR>"
        print(list(self.inports))
        format_ports = lambda ports: "".join(port_template.format(portname=port.name) for port_name, port in ports)
        inports = format_ports(self.inports)
        outports = format_ports(self.outports)
        inrow = row_template.format(ports=inports) if len(inports) > 0 else ""
        outrow = row_template.format(ports=outports) if len(outports) > 0 else ""
        table_template = """<
                    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="0">
                            {inrow}
                            <TR><TD VALIGN="MIDDLE" COLSPAN="10" BGCOLOR="{color}">{name}</TD></TR>
                            {outrow}
                    </TABLE>>"""

        return table_template.format(color=self.color, name=self.name, inports=inports, outports=outports, inrow=inrow,
                                     outrow=outrow)

    def gv_node(self):
        st = """node[shape=plaintext]
                {name} [label={lab}]""".format(c=self.color, name=str(self), lab=self.port_table())
        return st


    async def __call__(self):
        #Receive
        data = []
        for p_name, p in self.inports:
            received = await p.receive()
            data.append(received)
        transformed = self._f(data)
        print(data)
        #Send
        for p_name, p in self.outports:
            await p.send(transformed)


    def connect(self, other, outport, inport):
        c = Connection(self, other, outport, inport)
        if outport in self._outports:
            self._outports[outport].connect(c)
        if inport in other._inports:
            other._inports[inport].connect(c)
        return c


    @property
    def outports(self):
        yield from self._outports.items()

    @property
    def inports(self):
        yield from self._inports.items()


class Node:
    def __init__(self, name, f=lambda x: None):
        # Each node has a name
        self.name = name
        # Nodes are stored as dicts
        self._in = {}
        self._out = {}
        # This is the function that the node will execute
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
            for incoming_node in self.incoming:
                print("{}, receiving on {}".format(self.name, incoming_node))
                current_data = await self.channel.receive()
                self.data.append(current_data)
                return
        return data

    async def send_downstream(self, data):
        if self.n_out > 0:
            for outgoing_node in self.outgoing:
                print("{}, sending {} to {}".format(self.name, data, outgoing_node))
                # send data to the node
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
            if self.n_in == 0:
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
