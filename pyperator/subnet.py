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
        while True:
            pack = await self.inputs.IN.receive_packet()
            await self.outputs.OUT.send_packet(pack.copy())
            await asyncio.sleep(0)

class SubOut(SubIn):
    """
    This class implements an output
    for a subgraph
    """
    def __init__(self, name, **kwargs):
        super(SubOut, self).__init__(name, **kwargs)




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

    @classmethod
    def from_graph(cls, graph):
        #Add nodes

        g = cls(graph.name)
        #Copy the graph
        #Add an input for each exported inport
        for (in_name, in_port) in graph.inputs.items():
            #Now add a SubIn
            sub = SubIn('in_'+in_name)
            graph.add_node(sub)
            #Export the subin
            g.inputs.export(sub.inputs.IN,in_name)
            #connect subin and real port
            graph.connect(sub.outputs.OUT, in_port)
        for (out_name, out_port) in graph.outputs.items():
            #Now add a SubIn
            sub = SubIn('out_'+out_name)
            graph.add_node(sub)
            #Export the subin
            g.outputs.export(sub.outputs.OUT,out_name)
            #connect subin and real port
            graph.connect(out_port,sub.inputs.IN)
        g.nodes = graph._nodes
        return g


    async def __call__(self):
        for node in self.nodes:
            self.log.info("Component {} is a subnet, it will add its nodes to the"
                          " current executor.".format(self.name))
            self.dag.loop.create_task(node())




