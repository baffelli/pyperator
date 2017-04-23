from . import DAG
from . import components
from . import utils

class Subgraph(DAG.Multigraph):

    def __init__(self, name):
        super(Subgraph, self).__init__(name)
        self.inputs = utils.PortRegister(self)
        self.outputs = utils.PortRegister(self)
        print(DAG._global_dag.name)
        self.dag = DAG._global_dag or None
        if self.dag:
            [DAG._old_dag.add_node(node) for node in self.iternodes()]

    def export_input(self, port):
        for node in self.iternodes():
            if port in node.inputs:
                self.inputs.add(port)

    def export_output(self, port):
        for node in self.iternodes():
            if port in node.outputs.values():
                print('yes')
                self.outputs.add(port)
                return

    async def __call__(self):
        pass