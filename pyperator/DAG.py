import asyncio
import queue as _qu
import textwrap as _tw

from pyperator.utils import Connection

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
    def __init__(self):
        self._arcs = set()
        self._nodes = set()

    def connect(self, node1, node2, outport, inport):
        # Add nodes that are not in the node list
        [self._nodes.add(node) for node in [node1, node2] if not self.hasnode(node)]
        c = node1.connect(node2, outport, inport)
        self._arcs.add(c)

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
            yield from self._arcs

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
        arc_str = ("{} -> {}".format(a, b) for a, b in self.iterarcs())
        out_str = "\n".join(arc_str)
        return out_str

    def dot(self):
        nodes_gen = (node.gv_node() for node in self.iternodes())
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
            """.format(nodes=";\n".join(nodes_gen), edges="\n".join(arc_str))
        return _tw.dedent(graph_str)

    async def prime(self):
        for node in self.iternodes():
            for inbound_name, inbound in node.inports:
                await inbound._connection.send(None)

    def __call__(self):
        loop = asyncio.get_event_loop()
        # Find nodes with no predecessors
        a = [el for el in self.iternodes()]
        #Prime the network
        # loop.run_until_complete(self.prime())
        # print('Done priming')
        # #Execute them
        while True:
            coros = [c() for c in a]
            #Prime the network
            loop.run_until_complete(asyncio.gather(*coros))
            #
            #     except StopIteration:
            #         print('Computation completed')

# #Two generators
# simple_gen = (i for i in range(40))
# reverse_gen = (2 for i in range(40))
# #A simple sum process
# @process
# def sum_messages(a=None, b=None):
#     return a+b
#
#
#
#
# #Simple network
# a = Node('a', lambda x: next(simple_gen))
# b = Node('b', lambda x: next(reverse_gen))
# c = Node('c', sum_messages)
# d = Node('d', lambda x: print(x))
# graph = DAG()
# graph.add_arc(a, c)
# graph.add_arc(b, c)
# graph.add_arc(c, d)
# #Save
# with open('a.dot', 'w+') as of:
#     of.write(graph.dot())
#
# #Execute
# graph()
