import queue as _qu
import textwrap as _tw
import asyncio

from pype.nodes import Node
from pype.utils import process

cycle_str = 'Graph contains cycle beteween {} and {}'


def find_path(dag, start, end, path=[]):
    path  = path + [start]
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


class DAG:
    def __init__(self):
        self._arcs = {}
        self._nodes = set()

    def add_arc(self, node1, node2):
        # Add nodes that are not in the node list
        [self._nodes.add(node) for node in [node1, node2] if not self.hasnode(node)]
        #If
        try:
            self._arcs[node1].add(node2)
        except KeyError:
            self._arcs[node1] = set([node2])
        #Add incoming and outgoing to node
        node1.add_outgoing(node2)
        node2.add_incoming(node1)

    def hasarc(self, node1, node2):
        return node1 in self._arcs and node2 in self._arcs[node1]


    def hasnode(self, node):
        return node in self._nodes

    def remove_arc(self, node1, node2):
        #Remove arc from dict
        if node1 in self._arcs and node2 in self._arcs[node1]:
            self._arcs[node1].remove(node2)
        #Remove connection from incoming and outgoing
        node1.remove_outgoing(node2)
        node2.remove_incoming(node1)

    def iternodes(self):
        return self._nodes.__iter__()

    def adjacent(self, node):
        if node in self._arcs:
            yield from self._arcs[node]
        else:
            return

    def iterarcs(self):
        for node in self.iternodes():
            for adjacent_node in self.adjacent(node):
                yield (node, adjacent_node)

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
        nodes_gen =(node.gv_node() for node in self.iternodes())
        arc_str = ("{} -> {}".format(a, b) for a, b in self.iterarcs())
        # edged_gen
        graph_str = """
            digraph DAG{{
            graph[bgcolor=white, margin=0]
                {nodes}
                {edges}
            }}
            """.format(nodes="\n".join(nodes_gen), edges="\n".join(arc_str))
        return _tw.dedent(graph_str)

    def  __call__(self):
        loop = asyncio.get_event_loop()
        #Find nodes with no predecessors
        a = [el for el in self.iternodes() if not el.has_predecessor and el.n_out > 0]
        # #Execute them

        coros = [c() for c in a]
        coros[0].send(None)
        coros[1].send(None)
        coros[0].send(None)


        # while True:
        #     try:
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





