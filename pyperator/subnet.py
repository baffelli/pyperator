from pyperator.DAG import Multigraph
from pyperator.utils import InputPort, OutputPort
from pyperator.nodes import Component
import asyncio

class SubIn(Component):
    """
    This class implements an input
    for a subgraph
    """
    def __init__(self, name, **kwargs):
        super(SubIn, self).__init__(name, **kwargs)
        self.inputs.add(InputPort('IN'))
        self.outputs.add(OutputPort('OUT', optional=False))


    async def __call__(self):
        if self.inputs.IN._iip:
            pack = await self.inputs.IN.receive_packet()
            await self.outputs.OUT.send_packet(pack.copy())
            await self.outputs.OUT.close()
        else:
           async for pack in self.inputs.IN:
                await self.outputs.OUT.send_packet(pack.copy())
                await asyncio.sleep(0)

class SubOut(SubIn):
    """
    This class implements an output
    for a subgraph
    """
    def __init__(self, name, **kwargs):
        super(SubOut, self).__init__(name, **kwargs)

    async def __call__(self):
       async for pack in self.inputs.IN:
            print(pack)
            await self.outputs.OUT.send_packet(pack.copy())
            await asyncio.sleep(0)


class Subnet(Component):
    """
    This class implements a subnet
    with a separate workdir and a nicer
    visualization. Subnets can be still added
    by instantiating a normal graph, exporting
    ports and connecting it into an existing graph
    but this method is recommended.
    """

    def __init__(self, name, **kwargs):
        super(Subnet, self).__init__(name, **kwargs)
        self.subgraph = None

    @classmethod
    def from_graph(cls, graph):
        #Add nodes
        g = Subnet(graph.name)
        #Copy the graph
        #Add an input for each exported inport
        with graph as sg:
            for (in_name, in_port) in sg.inputs.items():
                #Now add a SubIn
                sub = SubIn('in_'+in_name)
                sg._nodes.add(sub)
                #Remove input port
                g.inputs.export(sub.inputs.IN, in_name)
                # connect subin and real port
                sg.connect(sub.outputs.OUT, in_port)
            for (out_name, out_port) in sg.outputs.items():
                #Now add a SubIn
                sub = SubOut('out_'+out_name)
                sg._nodes.add(sub)
                #Export the subin
                g.outputs.export(sub.outputs.OUT,out_name)
                #connect subin and real port
                sg.connect(out_port,sub.inputs.IN)
            g.subgraph = sg
            g.subgraph.log = g.dag.log.getChild(g.name)

        return g



    async def __call__(self):
        self.log.info("Component {} is a subnet, it will add its nodes to the"
                      " current executor.".format(self.name))
        for node in self.subgraph.iternodes():
            print(node)
            self.dag.loop.create_task(node())





