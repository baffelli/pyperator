from .utils import Connection
from .utils import Port

class Component:
    def __init__(self, name, f=lambda x: None, inputs=[], outputs=[]):
        self.name = name
        self.data = {}
        # Input and output ports
        self._inports = {}
        self._outports = {}
        # Function of the node
        self.color = 'grey'
        self._f = f
        self._ncall = 0
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

    async def prime(self):
        for p_name, p in self.inports:
            print('Sending None through {}'.format(p._connection))
            await p._connection.send(None)

    async def receive(self):
        data = {}
        for p_name, p in self.inports:
            received = await p.receive()
            data[p_name] = received
        return data

    async def send(self, data):
        # Send
        for p_name, p in self.outports:
            await p.send(data.get(p_name))


        return

    async def __call__(self):
        await self.prime()
        data = await self.receive()
        #Work
        transformed = self._f(**data)
        await self.send(transformed)








    def connect(self, other, outport, inport):
        c = Connection(self, other, outport, inport)
        if outport in self._outports:
            self._outports[outport].connect(c)
        if inport in other._inports:
            other._inports[inport].connect(c)
        return c

    @property
    def n_in(self):
        return len(self._inports)

    @property
    def n_out(self):
        return len(self._outports)

    @property
    def outports(self):
        yield from self._outports.items()

    @property
    def inports(self):
        yield from self._inports.items()


