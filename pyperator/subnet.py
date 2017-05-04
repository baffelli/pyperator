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
        self.outputs.add(OutputPort('OUT'))


    async def __call__(self):
        while True:
            pack = await self.inputs.IN.receive_packet()
            await self.outputs.OUT.send_packet(pack.copy())
            await asyncio.sleep(0)






class Subnet(Multigraph):
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
