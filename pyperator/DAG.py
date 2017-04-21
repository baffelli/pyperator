import asyncio
import logging
import os as _os
import textwrap as _tw

import __main__ as main

from . import exceptions
from . import logging as _log


import traceback

import concurrent.futures


_global_dag = None



class Multigraph():
    def __init__(self, log_path=None, name='DAG', log_level=logging.DEBUG, workdir=None):
        self._nodes = set()
        self.name = name
        self.workdir = workdir or './'
        self._log_path = self.workdir + self.name + '.log' or log_path or main.__file__.replace('.py', '.log')
        self.name = name or _os.path.basename(main.__file__)
        self._log = _log.setup_custom_logger(self.name, file=self._log_path, level=log_level)
        self.log.info("Created DAG with workdir {}".format(self.workdir))

    @property
    def workdir(self):
        if self._workdir:
            return self._workdir
        else:
            return ""

    @workdir.setter
    def workdir(self, dir):
        self._workdir = dir

    @property
    def log(self):
        if self._log:
            return self._log
        else:
           return _log.setup_custom_logger('buttavia')

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

    def disconnect(self, node1, node2):
        # TODO implement it
        pass

    def iternodes(self):
        return self._nodes.__iter__()

    def iterarcs(self):
        for source in self.iternodes():
            for name, port in source.outputs.items():
                for dest in port.iterends():
                    yield (port, dest)

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

    def __repr__(self):
        arc_str = ("{} -> {}".format(conn.gv_string(), conn.gv_string()) for conn in self.iterarcs())
        out_str = "\n".join(arc_str)
        return out_str

    def dot(self):
        # List of nodes
        nodes_gen = (node.gv_node() for node in self.iternodes())
        # List of arcs
        arc_str = ("{} -> {}".format(k.gv_string(), v.gv_string()) for k, v in self.iterarcs())
        # IIPs as additional nodes
        iip_nodes = "\n".join(
            ["\n".join(["node [shape=box,style=rounded] {name} [label=\"{iip}\"]".format(name=id(iip), iip=iip) for (port, iip)
                        in node.inputs.iip_iter()]) for node in self.iternodes()])
        iip_arcs = "\n".join(
            ["\n".join(["{source} -> {dest}".format(source=id(iip), dest=port.gv_string()) for (port, iip)
                        in node.inputs.iip_iter()]) for node in self.iternodes()])
        graph_str = """
            digraph DAG{{
            graph[bgcolor=white, margin=0]
                {nodes}
                {iipnodes}
                {edges}
                {iiparcs}
            }}
            """.format(nodes=";\n".join(nodes_gen), edges="\n".join(arc_str), iipnodes=iip_nodes, iiparcs=iip_arcs)
        return _tw.dedent(graph_str)

    def __call__(self):
        loop = asyncio.get_event_loop()
        self.log.info('DAG {}: Starting DAG'.format(self.name))
        # The producers are all the nodes that have no inputs
        producers = asyncio.gather(*[asyncio.ensure_future(node()) for node in self.iternodes() if node.n_in == 0])
        self.log.info('DAG {}: Producers are {}'.format(self.name, producers))
        # Consumers are scheluded
        consumers = asyncio.gather(*[asyncio.ensure_future(node()) for node in self.iternodes() if node.n_in > 0])
        self.log.info('DAG {}: Consumers are {}'.format(self.name, consumers))
        self.log.debug('DAG {}: Running Tasks'.format(self.name))
        try:
            loop.run_until_complete(producers)
            loop.run_until_complete(consumers)
        except StopAsyncIteration as e:
            self.log.info('DAG {}: Received EOS'.format(self.name))
        except Exception as e:
            self.log.exception(e)
            self.log.info('DAG {}: Stopping DAG by cancelling scheduled tasks'.format(self.name))
            if not loop.is_closed():
                task = asyncio.Task.all_tasks()
                future = asyncio.gather(*(task))
                future.cancel()
                # consumers.cancel()
        finally:
            if loop.is_running():
                loop.stop()
                self.log.info('DAG {}: Stopping DAG'.format(self.name))
            self.log.info('DAG {}: Stopped'.format(self.name))
