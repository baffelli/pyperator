import asyncio
import logging
import os as _os
import shutil
import textwrap as _tw

import __main__ as main
from pyperator import context
from pyperator import nodes

from pyperator import exceptions
from pyperator import logging as _log


import warnings as _warn
import itertools as _iter

# class Graph(metaclass=ABCMeta):
#     """
#     This is the abstract graph from which the different types of graphs
#     used by pyperator are derived
#     """
#
#     @abstractmethod
#     def iternodes(self):
#         """
#         This methods is a generator
#         that yields all the nodes in the graph
#
#         :return:
#         A generator objects iterating over the nodes
#         """
#         pass
#
#     @abstractmethod
#     def iterarcs(self):
#         """
#         Generator that yields all arcs in the graph
#
#         :return:
#         A generator object that yields pairs of `(source, dest)`
#         """
#         pass
#
#     @abstractmethod
#     async def __call__(self):
#         pass
#
#
# class BipartiteGraph(Graph):
#     pass



def check_connections(graph):
    for node in graph.iternodes():
        for disconn_name, disconn_port in node.inputs.iter_disconnected():
            print(disconn_name)
            if not disconn_port.optional:
               node.log.warn("The following input port is disconnected {}:{}".format(disconn_port.component.name, disconn_port.name))
        for disconn_name, disconn_port in node.outputs.iter_disconnected():
            print(disconn_name)
            if not disconn_port.optional:
                node.log.warn("The following output port is disconnected {}:{}".format(disconn_port.component.name,
                                                                                      disconn_port.name))



class Multigraph(nodes.Component):
    """
    This is a Multigraph, used to represent a FBP-style network.
    In this cases, components are of type :class:`pyperator.nodes.AbstractComponent`. This
    class has several convience methods to easily add nodes to the network and connect them.
    For example, a network can be created with the context manager using 
    
    .. code-block:: python
        print("a")
    """

    def __init__(self, name, log=None, log_level=logging.DEBUG, workdir=None):
        super(Multigraph, self).__init__(name)
        self._nodes = set()
        self._name = name
        self.workdir = workdir or './'
        self._log_path = None or log
        self._log = _log.setup_custom_logger(self.name, file=self._log_path, level=log_level)
        self.log.info("Created DAG {} with workdir {}".format(self.name, self.workdir))


    @property
    def workdir(self):
        if self._workdir:
            return self._workdir
        else:
            return ""

    @workdir.setter
    def workdir(self, dir):
        self._workdir = dir



    def connect(self, port1, port2):
        # Add nodes that are not in the node list
        self.log.debug("DAG {}: Connecting {} to {}".format(self.name, port1, port2))
        for port in [port1, port2]:
            try:
                # Add log to every component
                port.component.dag = self
                port.component._log = self.log
                if not self.hasnode(port.component):
                    self._nodes.add(port.component)
            except:
                raise exceptions.PortNotExistingError('Port {} does not exist'.format(port))
                self.log.ERROR("Port {} does not exist".format(port))
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

    def disconnect(self, node1: nodes.Component, node2: nodes.Component ):
        # TODO implement it
        pass

    def iternodes(self) -> nodes.Component:
        """
        Iterate all nodes in the DAG.
        By delegating the inner iteration to the instances of
        :class:`pyperator.nodes.Component`
        it is very easy to recursively flatten
        subnets.
        
        :yields: `pyperator.nodes.Component` 
        """
        for node in self._nodes:
            yield from node.iternodes()

    def iterarcs(self):
        for source in self.iternodes():
            for port in list(source.outputs.values()):
                for dest in port.iterends():
                    yield (port, dest)


    def adjacent(self, node):
        if node in self._arcs:
            yield from self._arcs[node]
        else:
            return

    # Context manager
    def __enter__(self):
        global _global_dag
        self._old_dag = context._global_dag
        context._global_dag = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        context._global_dag = self._old_dag

    # /Context manager

    def __repr__(self):
        arc_str = ("{} -> {}".format(s.gv_string(), v.gv_string()) for s, v in self.iterarcs())
        out_str = "\n".join(arc_str)
        return out_str

    def gv_node(self):
        st = """subgraph cluster_{name} {{
                    {dot}  
                    color=blue;
                    label={lab};
                        }}""".format(c=self.color, name=id(self), lab=self.name, dot=self.graph_dot_table())
        return st





    def graph_dot_table(self):
        # List of nodes
        nodes_gen = (node.gv_node() for node in self.iternodes())
        # List of arcs
        arc_str = ("{} -> {} [arrowType=normal]".format(k.gv_string(), v.gv_string(), v.size) for k, v in
                   self.iterarcs())
        # IIPs as additional nodes
        iip_nodes = "\n".join(
            ["\n".join(
                ["node [shape=box,style=rounded] {name} [label=\"{iip}\"]".format(name=id(iip), iip=iip) for (port, iip)
                 in node.inputs.iip_iter()]) for node in self.iternodes()])
        iip_arcs = "\n".join(
            ["\n".join(["{source} -> {dest}".format(source=id(iip), dest=port.gv_string()) for (port, iip)
                        in node.inputs.iip_iter()]) for node in self.iternodes()])
        graph_str = """
                {nodes}
                {iipnodes}
                {edges}
                {iiparcs}
            """.format(nodes=";\n".join(nodes_gen), edges="\n".join(arc_str), iipnodes=iip_nodes, iiparcs=iip_arcs)
        return _tw.dedent(graph_str)

    def dot(self):
        graph_str = """
            digraph DAG{{
            graph[bgcolor=white, margin=0]
                {graph_table}
            }}
            """.format(graph_table=self.graph_dot_table())
        return _tw.dedent(graph_str)

    def __call__(self):
        # Add code to the repository
        loop = asyncio.get_event_loop()
        self.loop = loop
        self.log.info('Starting DAG')
        self.log.info('has following nodes {}'.format(list(self.iternodes())))
        try:
            tasks = [asyncio.ensure_future(node) for node in self.iternodes()]
            loop.run_until_complete(asyncio.gather(*tasks))
        except StopAsyncIteration as e:
            self.log.info('Received EOS')
        except Exception as e:
            self.log.exception(e)
            self.log.info('Stopping DAG by cancelling scheduled tasks')
            if not loop.is_closed():
                task = asyncio.Task.all_tasks()
                future = asyncio.gather(*(task))
                future.cancel()
        finally:
            if loop.is_running():
                loop.stop()
                self.log.info('Stopping DAG')
            self.log.info('Stopped')
