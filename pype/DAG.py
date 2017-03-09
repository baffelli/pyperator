import queue as _qu
import textwrap as _tw


class Node:
    def __init__(self, name):
        self.name = name
        self._data = None
        self._in = set()
        self._out = set()

    def __repr__(self):
        st = "{}".format(self.name)
        return st

    @property
    def outgoing(self):
        yield from self._out

    @property
    def incoming(self):
        yield from self._in

    @property
    def has_predecessor(self):
        if self._in:
            return True


def add_arc(arcs, node1, node2):
    try:
        arcs[node1].add(node2)
    except KeyError:
        arcs[node1] = set([node2])


def remove_arc(arcs, node1, node2):
    for k, v in arcs.items():
        if k == node1 and node2 in v:
            v.remove(node2)
        arcs[k] = v
    return arcs


def find_path(dag, start, end, path=[]):
    path = path + [start]
    if start not in dag._nodes:
        return None
    if start == end:
        return path
    for node in dag.adjacent(start):
        print(path, node)
        if node in path:
            raise ValueError('Graph contains cycle')
        if node not in path:
            newpath = find_path(dag, node, end, path=path)
            if newpath: return newpath
    return None


def topological_sort(dag):
    T = []
    Q = _qu.LifoQueue()
    # Put all elements on queue that have no predecessor
    a = [el for el in dag.iternodes() if not el.has_predecessor]
    print(a)
    while not Q.empty():
        u = Q.get()
        print(list(u.outgoing))
        T.append(u)
    print(T)


class DAG:
    def __init__(self):
        self._arcs = {}
        self._nodes = set()

    def add_arc(self, node1, node2):
        # if node1 in self._nodes and node2 in self._nodes:
        # Add nodes that are not in the node list
        [self._nodes.add(node) for node in [node1, node2] if not self.hasnode(node)]
        if node1 not in self._nodes:
            self._nodes.add(node1)
        self._nodes.add(node2)
        add_arc(self._arcs, node1, node2)
        node1._out.add(node2)
        node2._in.add(node1)

    def hasnode(self, node):
        return node in self._nodes

    def remove_arc(self, node1, node2):
        self._arcs = remove_arc(self._arcs, node1, node2)
        self._nodes.node1._out.remove(node2)
        node2._out.remove(node1)

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
                    print('cycle')
                    # raise ValueError('Detected cycle')
                    return

        for node in self.iternodes():
            for visited_node in inner_dfs(self, node):
                yield visited_node

    def __repr__(self):
        arc_str = ("{} -> {}".format(a, b) for a, b in self.iterarcs())
        out_str = "\n".join(arc_str)
        return out_str

    def dot(self):
        nodes_gen = map(str, self.iternodes())
        arc_str = ("{} -> {}".format(a, b) for a, b in self.iterarcs())
        # edged_gen
        graph_str = """
            digraph DAG{{
            graph[bgcolor=white, margin=0];
            node[shape=box, style=rounded, fontname=sans, \
                fontsize=10, penwidth=2];
                edge[penwidth=2, color=grey];
                {nodes}
                {edges}
            }}
            """.format(nodes="\n".join(nodes_gen), edges="\n".join(arc_str))
        return _tw.dedent(graph_str)


a = Node('a')
b = Node('b')
c = Node('c')
d = Node('d')
e = Node('e')

graph = DAG()

# Add nodes
# graph.add_node(a)
# graph.add_node(b)
# graph.add_node(c)
# graph.add_node(d)
# graph.add_node(e)
# Connect them
graph.add_arc(a, b)
graph.add_arc(b, c)
graph.add_arc(c, d)
graph.add_arc(c, e)
graph.add_arc(c, c)
print(list(c.outgoing))
topological_sort(graph)

print(str(graph))
with open('a.dot', 'w+') as of:
    of.write(graph.dot())
