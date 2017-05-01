import asyncio

from pyperator import DAG
from pyperator import context
from pyperator import nodes
from pyperator import utils
from pyperator.utils import log_schedule
from pyperator import DAG

class Subgraph(DAG.Multigraph):
    def __init__(self, name, **kwargs):
        super(Subgraph, self).__init__(name)
        self.color = 'grey'

    @classmethod
    def from_graph(cls, name, graph):
        sub = Subgraph(name)
        sub.name = name
        sub._nodes = graph._nodes
        sub.inputs = graph.inputs
        sub.outputs = graph.outputs
        return sub


    def __enter__(self):
        self.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__exit__(exc_type, exc_val, exc_tb)

    @property
    def log(self):
        if self.dag:
            return self.dag.log

    def gv_node(self):
        st = """subgraph cluster_{name} {{
                    {dot}  
                    color=blue;
                    label={lab};
                        }}""".format(c=self.color, name=id(self), lab=self.name, dot=self.graph_dot_table())
        return st

    @log_schedule
    async def __call__(self):
        if self.dag:
            self.log.info(
                "Component {} is a subgraph: Adding all nodes to the executor of {}".format(self.name, self.dag.name))
            asyncio.ensure_future(asyncio.gather(*[node() for node in self.iternodes()]), loop=self.dag.loop)
        return
