from .utils import InputPort, OutputPort, PortRegister
import asyncio


async def receive_future_data(futures):
    result = {}
    for k,v in futures.items():
        result[k] = await v
    return result

class Component:
    def __init__(self, name, f=lambda x: None, inputs=[], outputs=[]):
        self.name = name
        self.data = {}
        # Input and output ports
        self.inputs = PortRegister(self)
        self.outputs = PortRegister(self)
        # Function of the node
        self.color = 'grey'
        self._f = f
        self._active = asyncio.Queue()
        # initalize ports
        for inport in inputs:
            self.inputs.update({inport: InputPort(inport, component=self)})
        for outport in outputs:
            self.outputs.update({outport: OutputPort(outport, component=self)})


    def __repr__(self):
        st = "{}".format(self.name)
        return st


    def port_table(self):

        port_template = "<TD PORT=\"{portname}\">{portname}</TD>"
        row_template = "<TR>{ports}</TR>"
        format_ports = lambda ports: "".join(port_template.format(portname=port.name) for port in ports)
        inports = format_ports(self.inputs.values())
        outports = format_ports(self.outputs.values())
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


    def receive(self):
        futures = {}
        for p_name, p in self.inputs.items():
            received = asyncio.ensure_future(p.receive())
            futures[p_name] = received
        return futures

    def send(self, data):
        # Send
        futures = []
        for p_name, p in self.outputs.items():
            futures.append(asyncio.ensure_future(p.send(data)))
        return futures


    async def dot(self,):
        return self.gv_node()


    async def active(self):
        self.color = 'green'
        # await self._active.put(self.color)


    async def inactive(self):
        # await self._active.put(self.color)
        self.color = 'grey'

    async def __call__(self):
        while True:
            await self.active()
            #Get the futures for the inputs
            future_inputs = self.receive()
            data = await receive_future_data(future_inputs)
            print(self, data)
            #Work
            transformed_data = await self._f(**data)
            print(transformed_data)
            print(transformed_data)
            #Run downstream
            future = self.send(transformed_data)
            await self.inactive()
            await asyncio.sleep(0)


    @property
    def n_in(self):
        return len(self.inputs)

    @property
    def n_out(self):
        return len(self.outputs)



    @property
    def successors(self):
        yield from (port._connection.dest  for port_name, port in self._outports.items())



