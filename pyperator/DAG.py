import asyncio
import queue as _qu
import textwrap as _tw
from aiohttp import web
# from .gui import create_gui
from . import logging as _log
import logging

from . import utils as _ut


_log.setup_custom_logger('root')


class Multigraph:
    def __init__(self):
        self._arcs = {}
        self._nodes = set()
        self._workdir = None
        logging.getLogger('root').info("Created DAG")

    @property
    def workdir(self):
        return self._workdir

    @workdir.setter
    def workdir(self, dir):
        self._workdir = dir

    def connect(self, port1, port2):
        # Add nodes that are not in the node list
        logging.getLogger('root').debug("Connecting {} to {}".format(port1,port2))
        for port in [port1, port2]:
            try:
                if not self.hasnode(port.component):
                    self._nodes.add(port.component)
            except:
                raise _ut.PortNotExistingException('Port {} does not exist'.format(port))
                logging.getLogger('root').ERROR("Port {} does not exist".format(port))
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
        producers = asyncio.gather(*[asyncio.ensure_future(node()) for node in self.iternodes() if node.n_in == 0])
        logging.getLogger('root').debug('Producers are {}'.format(producers))
        #Consumers are scheluded
        consumers = asyncio.gather(*[asyncio.ensure_future(node()) for node in self.iternodes() if node.n_in >0])
        logging.getLogger('root').debug('Consumers are {}'.format(consumers))
        # try:
        logging.getLogger('root').info('Starting DAG')
        logging.getLogger('root').debug('Running Producers until they complete')
        try:
            loop.run_until_complete(producers)
            loop.run_until_complete(consumers)
        except Exception as e:
            print(e)
            logging.getLogger('root').error(e)
            logging.getLogger('root').info('Stopping DAG by closing consumers')
            if not loop.is_closed():
                # producers.cancel()
                consumers.cancel()
        finally:
            if loop.is_running():
                loop.stop()
                logging.getLogger('root').info('Stopping DAG')

