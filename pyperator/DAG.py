import asyncio
import textwrap as _tw
# from .gui import create_gui
from . import exceptions
from . import logging as _log
import logging

from . import utils as _ut


import os as _os

from . import nodes

import __main__ as main


_global_dag = None




class Multigraph():
    def __init__(self, log_path=None, name=None, log_level=logging.DEBUG):
        # self._arcs = {}
        self._nodes = set()
        self._workdir = None
        self._log_path = log_path or main.__file__.replace('.py', '.log')
        self.name = name or _os.path.basename(main.__file__)
        self._log = _log.setup_custom_logger(self.name, file=self._log_path, level=log_level)
        self._log.info("Created DAG")

    @property
    def workdir(self):
        return self._workdir

    @workdir.setter
    def workdir(self, dir):
        self._workdir = dir

    def connect(self, port1, port2):
        # Add nodes that are not in the node list
        self._log.debug("DAG {}: Connecting {} to {}".format(self.name, port1,port2))
        for port in [port1, port2]:
            try:
                #Add log to every component
                port.component.dag = self
                port.component._log = self._log
                if not self.hasnode(port.component):
                    self._nodes.add(port.component)
            except:
                raise exceptions.PortNotExistingError('Port {} does not exist'.format(port))
                self._log.ERROR("Port {} does not exist".format(port))
        port1.connect(port2)
        # self._arcs.update(port1.connect_dict)


    def set_initial_packet(self, port, value):
        port.set_initial_packet(value)

    def set_kickstarter(self, port):
        port.kickstart()

    def add_node(self, node):
        node.dag = self
        node._log = self._log
        self._nodes.add(node)


    def __radd__(self, other):
        self.add_node(other)
        return self

    def __add__(self, other):
        self.add_node(other)
        return self


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
        for source in self.iternodes():
            for name,port in source.outputs.items():
                for dest in port.iterends():
                    yield (port, dest)


    # def iterarcs(self):
    #     for source in self._arcs.keys():
    #         for dest in source.iterends():
    #             yield (source, dest)


    def adjacent(self, node):
        if node in self._arcs:
            yield from self._arcs[node]
        else:
            return

    def __enter__(self):
        global _global_dag
        self._old_dag = _global_dag
        _global_dag = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _global_dag
        _global_dag = self._old_dag


    def dfs(self):
        """
        Depth first traversal
        """
        seen = set()

        def inner_dfs(G, start_node):
            seen.add(start_node)
            for node in G.adjacent(start_node):
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

    # async def dot_coro(self):
    #     while True:
    #         nodes = []
    #         future_nodes = [node._active.get() for node in self.iternodes()]
    #         completed, pending = await asyncio.wait(future_nodes,return_when=asyncio.FIRST_COMPLETED)
    #         for node in self.iternodes():
    #             print(node.color)
    #             dot =await node.dot()
    #             nodes.append(dot)
    #         arc_str = (
    #             "{source}:{outport} -> {dest}:{inport}".format(source=connection.source, dest=connection.dest,
    #                                                                         inport=connection.inport,
    #                                                                         outport=connection.outport) for
    #             connection in self.iterarcs())
    #         # edged_gen
    #         graph_str = """
    #             digraph DAG{{
    #             graph[bgcolor=white, margin=0]
    #                 {nodes}
    #                 {edges}
    #             }}
    #             """.format(nodes=";\n".join(nodes), edges="\n".join(arc_str))
    #         print(graph_str)
    #     return _tw.dedent(graph_str)




    def __call__(self):
        loop = asyncio.get_event_loop()
        self._log.info('DAG {}: Starting DAG'.format(self.name))
        #The producers are all the nodes that have no inputs
        producers = asyncio.gather(*[asyncio.ensure_future(node()) for node in self.iternodes() if node.n_in == 0])
        self._log.info('DAG {}: Producers are {}'.format(self.name, producers))
        #Consumers are scheluded
        consumers = asyncio.gather(*[asyncio.ensure_future(node()) for node in self.iternodes() if node.n_in >0])
        self._log.info('DAG {}: Consumers are {}'.format(self.name, consumers))
        self._log.debug('DAG {}: Running Tasks'.format(self.name))
        try:
            loop.run_until_complete(producers)
            loop.run_until_complete(consumers)
        except Exception as e:
            self._log.error(e)
            self._log.info('DAG {}: Stopping DAG by cancelling scheduled tasks'.format(self.name))
            if not loop.is_closed():
                task = asyncio.Task.all_tasks()
                future =asyncio.gather(*(task))
                future.cancel()
                # consumers.cancel()
        finally:
            if loop.is_running():
                loop.stop()
                self._log.info('DAG {}: Stopping DAG'.format(self.name))
            self._log.info('DAG {}: Stopped'.format(self.name))

