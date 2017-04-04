import asyncio
import queue as _qu
import textwrap as _tw
from aiohttp import web
# from .gui import create_gui
import logging as _log

from . import utils as _ut

# from pyperator.utils import Connection

cycle_str = 'Graph contains cycle beteween {} and {}'


def find_path(dag, start, end, path=[]):
    path = path + [start]
    yield start
    if start not in dag._nodes:
        raise ValueError('Node does not exist')
    if start == end:
        return
    for node in dag.adjacent(start):
        if node in path:
            raise ValueError(cycle_str.format(start, node))
        if node not in path:
            yield from  find_path(dag, node, end, path=path)


def topological_sort(dag):
    T = []
    Q = _qu.LifoQueue()
    # Put all elements on queue that have no predecessor
    a = [el for el in dag.iternodes() if not el.has_predecessor]
    print(a)
    while not Q.empty():
        u = Q.get()
        print(u)
        print(list(u.outgoing))
        T.append(u)
    print(T)


class Multigraph:
    def __init__(self, log_path=None):
        self._arcs = {}
        self._nodes = set()

    def connect(self, port1, port2):
        # Add nodes that are not in the node list
        for port in [port1, port2]:
            try:
                if not self.hasnode(port.component):
                    self._nodes.add(port.component)
            except:
                raise _ut.PortNotExistingException('Port {} does not exist'.format(port))
        port1.connect(port2)
        self._arcs.update(port1.connect_dict)

    def set_initial_packet(self, port, value):
        ports = [dest for (source, dest) in self.iterarcs() if dest==port]
        port.set_initial_packet(value)

    def hasarc(self, node1, node2, outport, inport):
        return node1 in self._arcs and {node2: (outport, inport)} in self._arcs[node1]

    def hasnode(self, node):
        return node in self._nodes




    def disconnect(self, node1, node2):
        # TODO implement it
        pass

    def iternodes(self):
        return self._nodes.__iter__()

    def iterarcs(self):
        for source in self._arcs.keys():
            for dest in source.iterends():
                yield (source, dest)


    def adjacent(self, node):
        if node in self._arcs:
            yield from self._arcs[node]
        else:
            return

    def dfs(self):
        """
        Depth first traversal
        """
        seen = set()

        def inner_dfs(G, start_node):
            seen.add(start_node)
            for node in G.adjacent(start_node):
                print("current node {}, seen {}".format(node, seen))
                if node not in seen:
                    seen.add(node)
                    yield node
                else:
                    # raise ValueError(cycle_str.format(start_node, node))
                    return

        for node in self.iternodes():
            print(node)
            yield from inner_dfs(self, node)

    def __repr__(self):
        arc_str = ("{} -> {}".format(conn.gv_string(), conn.gv_string()) for conn in self.iterarcs())
        out_str = "\n".join(arc_str)
        return out_str

    def dot(self):
        nodes_gen = (node.gv_node() for node in self.iternodes())
        arc_str = ("{} -> {}".format(k.gv_string(), v.gv_string()) for k, v in self.iterarcs())
        # edged_gen
        graph_str = """
            digraph DAG{{
            graph[bgcolor=white, margin=0]
                {nodes}
                {edges}
            }}
            """.format(nodes=";\n".join(nodes_gen), edges="\n".join(arc_str))
        return _tw.dedent(graph_str)

    async def dot_coro(self):
        while True:
            nodes = []
            future_nodes = [node._active.get() for node in self.iternodes()]
            completed, pending = await asyncio.wait(future_nodes,return_when=asyncio.FIRST_COMPLETED)
            for node in self.iternodes():
                print(node.color)
                dot =await node.dot()
                nodes.append(dot)
            arc_str = (
                "{source}:{outport} -> {dest}:{inport}".format(source=connection.source, dest=connection.dest,
                                                                            inport=connection.inport,
                                                                            outport=connection.outport) for
                connection in self.iterarcs())
            # edged_gen
            graph_str = """
                digraph DAG{{
                graph[bgcolor=white, margin=0]
                    {nodes}
                    {edges}
                }}
                """.format(nodes=";\n".join(nodes), edges="\n".join(arc_str))
            print(graph_str)
        return _tw.dedent(graph_str)




    def __call__(self):
        loop = asyncio.get_event_loop()
        #The producers are all the nodes that have no inputs
        producers = [asyncio.ensure_future(node()) for node in self.iternodes() if node.n_in == 0]
        #Consumers are scheluded
        consumers = [asyncio.ensure_future(node()) for node in self.iternodes() if node.n_in >0]
        try:
            loop.run_until_complete(asyncio.gather(*producers))
        except Exception as e:
            print(e)
        finally:
            loop.close()
