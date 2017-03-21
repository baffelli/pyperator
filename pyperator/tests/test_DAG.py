from unittest import TestCase

from pyperator.nodes import Node as Node
from ..DAG import DAG as DAG

class TestDAG(TestCase):


    def test_add_arc(self):
        a = Node('a')
        b = Node('b')
        graph = DAG()
        graph.add_arc(a, b)

        #Check if arc exists
        self.assertTrue(graph.hasarc(a,b))
        #Check if the incoming and outgoing lists
        #are correct
        self.assertTrue(b in a.outgoing)
        self.assertTrue(a in b.incoming)
        #Check if the channel is the same
        self.asserEqual(a._out[b], b._in[a])

    def test_remove_arc(self):
        #Create example graph
        a = Node('a')
        b = Node('b')
        graph = DAG()
        graph.add_arc(a, b)
        #Remove arc
        graph.remove_arc(a,b)
        self.assertFalse(graph.hasarc(a, b))
        self.assertFalse(b in a.outgoing)
        self.assertFalse(a in b.incoming)

    def test_iternodes(self):
        a = Node('a')
        b = Node('b')
        graph = DAG()
        graph.add_arc(a, b)
        self.assertTrue(set(graph.iternodes()), graph._nodes)

    def test_adjacent(self):
        self.fail()

    def test_iterarcs(self):
        self.fail()

    def test_dfs(self):
        self.fail()

    def test_dot(self):
        self.fail()
