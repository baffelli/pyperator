from pyperator.DAG import Multigraph


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
