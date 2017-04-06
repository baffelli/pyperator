from unittest import TestCase

from ..DAG import  Multigraph
from ..components import GeneratorSource, ShowInputs, BroadcastApplyFunction, ConstantSource, Filter, OneOffProcess
from .. import components
from ..nodes import Component
import asyncio
from ..utils import InputPort, OutputPort, FilePort
from .. import IP

import os
import uuid


async def printer(**kwargs):
    print("Inputs are {}".format(kwargs))
    return

def adder(**kwargs):
    out = sum([item for k, item in kwargs.items() if item])
    return out


async def passer(**kwargs):
    await asyncio.sleep(0.2)
    print(kwargs)
    return {'delayed': kwargs.values()}

source_gen = (i for i in range(100))


class TestPacket(TestCase):

    def testRepr(self):
        a = IP.InformationPacket('a')
        print(str(a))

    def testFilePacket(self):
        unique_file = os.path.dirname(__file__) + '/' + str(uuid.uuid4())
        b = IP.FilePacket(unique_file)
        print(str(b))

class TestMultigraph(TestCase):


    def testNormalPort(self):
        c1 = Component('c1')
        c1.outputs.add(OutputPort('a'))
        c2 = Component('c2')
        c2.inputs.add(InputPort('b'))
        graph = Multigraph()
        graph.connect(c1.outputs['a'], c2.inputs['b'])
        with open('/home/baffelli/normal.dot','w+') as outfile:
            outfile.write(graph.dot())

    def testArrayPort(self):
        c1 = Component('c1')
        c1.outputs.add(OutputPort('a'))
        c2 = Component('c2')
        c2.inputs.add(InputPort('b'))
        c2.inputs.add(InputPort('c'))
        graph = Multigraph()
        graph.connect(c1.outputs['a'], c2.inputs['b'])
        graph.connect(c1.outputs['a'], c2.inputs['c'])
        print(list(graph.iterarcs()))
        with open('/home/baffelli/multiport.dot','w+') as outfile:
            outfile.write(graph.dot())

    def testMultipleConnection(self):
        c1 = Component('c1')
        c1.outputs.add(OutputPort('a'))
        c1.outputs.add(OutputPort('b'))
        c2 = Component('c2')
        c2.inputs.add(InputPort('a'))
        graph = Multigraph()
        graph.connect(c1.outputs.a, c2.inputs.a)
        graph.connect(c1.outputs.b, c2.inputs.a)


    def testPortUniqueness(self):
        """Test if ports with the same name are unique"""
        p1 = InputPort('b')
        p2 = InputPort('b')
        self.assertFalse(p1 == p2)


    def testPortRegister(self):
        c1 = Component('c1')
        c1.outputs.add(OutputPort('a'))
        c1.outputs.add(OutputPort('b'))
        self.assertEquals(c1.outputs.a, c1.outputs['a'])

    def testSendReceive(self):
        c1 = Component('c1')
        c1.outputs.add(OutputPort('a'))
        c2 = Component('c2')
        c2.outputs.add(OutputPort('b'))
        c3 = Component('c3')
        c3.inputs.add(InputPort('in1'))
        c3.inputs.add(InputPort('in2'))
        graph = Multigraph()
        graph.connect(c1.outputs['a'], c3.inputs['in1'])
        graph.connect(c2.outputs['b'], c3.inputs['in2'])
        # graph.set_initial_packet(c3.inputs['in1'], 6)
        async def send(messages):
            for m in messages:
                await asyncio.sleep(0.2)
                [asyncio.ensure_future(c1.outputs['a'].send_to_all(m)), asyncio.ensure_future(c2.outputs['b'].send_to_all(m))]

            asyncio.ensure_future(c1.outputs['a'].close())
            asyncio.ensure_future(c2.outputs['b'].close())
        async def receive():
            while True:
                print(c3.inputs['in1'].queue)
                res, doing = await asyncio.wait([c3.inputs['in1'].receive(),c3.inputs['in2'].receive()], return_when=asyncio.ALL_COMPLETED)
                print('done receiving')
                print(res.pop().result(),res.pop().result())
                # await asyncio.sleep(0)
        futures = [asyncio.ensure_future(send([1,2,3,4,5])),asyncio.ensure_future(receive())]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(futures[1])


    def testLinearPipeline(self):
        source = GeneratorSource('s', source_gen)
        shower = ShowInputs('printer')
        shower.inputs.add(InputPort('in1'))
        graph = Multigraph()
        graph.connect(source.outputs['OUT'], shower.inputs['in1'])
        graph()

    def testSumPipeline(self):
        source1 = GeneratorSource('s1',  (i for i in range(100)))
        source2 = GeneratorSource('s2',  (i for i in range(100)))
        shower = ShowInputs('printer')
        shower.inputs.add(InputPort('in1'))
        summer = BroadcastApplyFunction('summer', adder )
        summer.inputs.add(InputPort('g1'))
        summer.inputs.add(InputPort('g2'))
        summer.outputs.add(OutputPort('sum'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, summer.inputs.g1)
        graph.connect(source2.outputs.OUT, summer.inputs.g2)
        graph.connect(summer.outputs.sum, shower.inputs.in1)
        with open('/home/baffelli/sum.dot','w+') as outfile:
            outfile.write(graph.dot())
        graph()

    def testRecursivePipeline(self):
        source1 = GeneratorSource('s1',  (i for i in range(1000)))
        shower = ShowInputs('printer')
        shower.inputs.add(InputPort('in1'))
        summer = BroadcastApplyFunction('summer', adder )
        summer.inputs.add(InputPort('g1'))
        summer.inputs.add(InputPort('recursion'))
        summer.outputs.add(OutputPort('sum'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, summer.inputs.g1)
        graph.connect(summer.outputs.sum, shower.inputs.in1)
        graph.connect(summer.outputs.sum, summer.inputs.recursion)
        #Add a kickstarter to a port
        graph.set_kickstarter(summer.inputs.recursion)
        with open('/home/baffelli/recursion.dot','w+') as outfile:
            outfile.write(graph.dot())
        graph()

    def testConstantSource(self):
        source1 = ConstantSource('s1', 3)
        shower = ShowInputs('printer')
        shower.inputs.add(InputPort('in1'))
        graph = Multigraph()
        graph.connect(source1.outputs['OUT'], shower.inputs.in1)
        graph()



    def testOneOffProcess(self):
        source1 = ConstantSource('s1', 3)
        source2 = OneOffProcess('of', lambda kwargs: 5)
        source2.outputs.add(OutputPort('s2'))
        summer = BroadcastApplyFunction('summer', adder )
        summer.inputs.add(InputPort('g1'))
        summer.inputs.add(InputPort('g2'))
        summer.outputs.add(OutputPort('sum'))
        shower = ShowInputs('printer', inputs=['in1'])
        graph = Multigraph()
        graph.connect(source1.outputs['OUT'], summer.inputs.g1)
        graph.connect(source2.outputs['s2'], summer.inputs.g2)
        graph.connect(summer.outputs.sum, shower.inputs.in1)
        graph()

    def testInfiniteRecursion(self):
        source1 = ConstantSource('s1', 3)
        shower = ShowInputs('printer', inputs=['in1'])
        summer = BroadcastApplyFunction('summer', adder )
        summer.inputs.add(InputPort('in1'))
        summer.inputs.add(InputPort('recursion'))
        summer.outputs.add(OutputPort('sum'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, summer.inputs.in1)
        graph.connect(summer.outputs.sum, summer.inputs.recursion)
        graph.set_initial_packet(summer.inputs.recursion, 0)
        graph.connect(summer.outputs.sum, shower.inputs.in1)
        graph()

    def testSplit(self):
        source1 = ConstantSource('s1', (3,5))
        splitter = components.Split('split in two')
        splitter.outputs.add(OutputPort('a'))
        splitter.outputs.add(OutputPort('b'))
        shower = ShowInputs('printer')
        shower.inputs.add(InputPort('a'))
        shower.inputs.add(InputPort('b'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, splitter.inputs.IN)
        graph.connect(splitter.outputs.a, shower.inputs.a)
        graph.connect(splitter.outputs.b, shower.inputs.b)
        graph()

    def testFilter(self):
        def filter_predicate(in1=None):
            if in1 % 2 ==0:
                return True
            else:
                return False
        source1 = GeneratorSource('s1', (i for i in range(100)))
        filt = Filter('filtrator',  filter_predicate,)
        filt.inputs.add(InputPort('in1'))
        filt.outputs.add(OutputPort('out1'))
        shower = ShowInputs('printer')
        shower.inputs.add(InputPort('in1'))
        graph = Multigraph()
        graph.connect(source1.outputs['OUT'], filt.inputs.in1)
        graph.connect(filt.outputs.out1, shower.inputs.in1)
        graph()

    def testFixedFormatter(self):
        #generate uniquefilename
        unique_file = os.path.dirname(__file__) + '/' + str(uuid.uuid4())
        toucher = components.Shell('shell', "touch {outputs.f1}")
        toucher.outputs.add(FilePort('f1'))
        toucher.FixedFormatter('f1', unique_file)
        printer = ShowInputs('show path')
        printer.inputs.add(FilePort('f1'))
        graph = Multigraph()
        graph.connect(toucher.outputs.f1, printer.inputs.f1)
        graph()
        self.assertTrue(os.path.exists(unique_file))

    def testPatternFormatter(self):
        #Source
        source1 = GeneratorSource('s1', (i for i in range(5)))
        toucher = components.Shell('shell', "echo '{inputs.i.value}, {inputs.i.value} to {outputs.f1.path}' > {outputs.f1.path}")
        toucher.outputs.add(FilePort('f1'))
        toucher.inputs.add(InputPort('i'))
        toucher.DynamicFormatter('f1', "{inputs.i.value}.txt")
        printer = ShowInputs('show_path')
        printer.inputs.add(FilePort('f2'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, toucher.inputs.i)
        graph.connect(toucher.outputs.f1, printer.inputs.f2)
        graph()

    def testCombinatorialFormatter(self):
        #Source
        source1 = GeneratorSource('s1', (i for i in range(5)))
        source2 = GeneratorSource('s2', (i for i in range(5)))
        toucher = components.Shell('shell', "echo '{inputs.i.value}, {inputs.j.value}' > {outputs.f1.path}")
        toucher.outputs.add(FilePort('f1'))
        toucher.inputs.add(InputPort('i'))
        toucher.inputs.add(InputPort('j'))
        toucher.DynamicFormatter('f1', "{inputs.j.value}_{inputs.i.value}.txt1")
        printer = ShowInputs('show_path')
        printer.inputs.add(FilePort('f2'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, toucher.inputs.i)
        graph.connect(source2.outputs.OUT, toucher.inputs.j)
        graph.connect(toucher.outputs.f1, printer.inputs.f2)
        graph()

    def testShellFail(self):
        #Source
        source1 = GeneratorSource('s1', (i for i in range(5)))
        toucher = components.Shell('shell', "cara")
        toucher.outputs.add(FilePort('f1'))
        toucher.inputs.add(InputPort('i'))
        toucher.DynamicFormatter('f1', "{inputs.i.value}.test")
        printer = ShowInputs('show_path')
        printer.inputs.add(FilePort('f2'))
        graph = Multigraph(log_path='fail.log')
        graph.connect(source1.outputs.OUT, toucher.inputs.i)
        graph.connect(toucher.outputs.f1, printer.inputs.f2)
        graph()

    def testPatternStages(self):
        source1 = GeneratorSource('s1', (i for i in range(5)))
        #First component generates file
        toucher = components.Shell('echo', "echo '{inputs.i.value} to {outputs.f1.path}' > {outputs.f1.path}")
        toucher.inputs.add(InputPort('i'))
        toucher.outputs.add(FilePort('f1'))
        toucher.DynamicFormatter('f1', "{inputs.i.value}.txt")
        #Second component receives it
        modified = components.Shell('edit', "echo 'i saw {inputs.f1.path}' > {outputs.f2.path}")
        modified.inputs.add(FilePort('f1'))
        modified.outputs.add(FilePort('f2'))
        modified.DynamicFormatter('f2', "{inputs.f1.path}.changes")
        #Finally we need a sink to drive the network
        printer = ShowInputs('show_path')
        printer.inputs.add(FilePort('f2'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, toucher.inputs.i)
        graph.connect(toucher.outputs.f1, modified.inputs.f1)
        graph.connect(modified.outputs.f2, printer.inputs.f2)
        graph()


