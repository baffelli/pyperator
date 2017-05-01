from . import DAG
from . import utils
from . import nodes
import asyncio

from . utils import log_schedule

class Subgraph(nodes.Component):

    def __init__(self, name, **kwargs):
        super(Subgraph, self).__init__(name)
        self.inputs = utils.PortRegister(self)
        self.outputs = utils.PortRegister(self)
        self.color ='grey'
        self.graph = DAG.Multigraph(name, **kwargs)
        self.dag = DAG._global_dag or None
        if self.dag:
            print('here')
            self.dag.add_node(self)

    @classmethod
    def from_graph(cls, name, graph):
        sub = Subgraph(name)
        sub.name = name
        sub.graph = graph
        return sub


    def export_input(self, port, name):
        for node in self.graph.iternodes():
            if port in node.inputs.values():
                self.inputs.add_as(port, name)

    def export_output(self, port, name):
        for node in self.graph.iternodes():
            if port in node.outputs.values():
                self.outputs.add_as(port, name)
                return



    def __enter__(self):
        self.graph.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.graph.__exit__(exc_type, exc_val, exc_tb)

    @property
    def log(self):
        if self.dag:
            return self.dag.log



    def gv_node(self):
        st = """subgraph cluster_{name} {{
                    {dot}  
                    color=blue;
                    label={lab};
                        }}""".format(c=self.color, name=id(self), lab=self.name, dot=self.graph.graph_dot_table())
        return st

    @log_schedule
    async def __call__(self):
        if self.dag:
            self.log.info("Component {} is a subgraph: Adding all nodes to the executor of {}".format(self.name, self.dag.name))
            asyncio.ensure_future(asyncio.gather(*[node() for node in self.graph.iternodes()]), loop=self.dag.loop)
        return



