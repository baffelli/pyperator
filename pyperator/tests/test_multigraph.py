from unittest import TestCase

import pyperator.exceptions
import pyperator.shell
from pyperator.DAG import Multigraph
from pyperator.components import GeneratorSource, ShowInputs, BroadcastApplyFunction, ConstantSource, Filter, OneOffProcess
from pyperator import components
from pyperator.nodes import Component
import asyncio
from pyperator.utils import InputPort, OutputPort, FilePort, Wildcards
from pyperator import IP

from pyperator import subgraph

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

    def testCopy(self):
        a = IP.FilePacket('a')
        b = a.copy()
        print(a,b)

class TestWildcards(TestCase):

    def TestEscape(self):
        a = '{value}.{ext}'
        w = Wildcards(a)
        wildcards = w.parse('prova.txt')
        print(wildcards.__dict__)

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
        with self.assertRaises(pyperator.exceptions.MultipleConnectionError):
            graph.connect(c1.outputs.a, c2.inputs.a)
            graph.connect(c1.outputs.b, c2.inputs.a)



    def testNonExistingPort(self):
        c1 = Component('c1')
        with self.assertRaises(pyperator.exceptions.PortNotExistingError):
            c1.outputs.c

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


    def testOutputReceive(self):
        c1 = Component('c1')
        c1.outputs.add(OutputPort('a'))
        async def test():
            await c1.outputs.a.receive()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test())

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


    def testPortAiter(self):
        source = GeneratorSource('s')
        source.inputs.generator.set_initial_packet(source_gen)
        printer = ShowInputs('in')
        printer.inputs.add(InputPort('in1'))
        g = Multigraph()
        g.connect(source.outputs.OUT, printer.inputs.in1)
        async def receive_all():
            received = []
            print('receiving')
            async for s in printer.inputs.in1:
                received.append(s)
            print(received)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(source(),receive_all()))

    def testRegisterAiter(self):
        source = GeneratorSource('s', source_gen)
        printer = ShowInputs('in')
        printer.inputs.add(InputPort('in1'))
        g = Multigraph()
        g.connect(source.outputs.OUT, printer.inputs.in1)
        async def receive_all():
            received = []
            print('receiving')
            async for s in printer.inputs:
                received.append(s)
            print(received)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(source(),receive_all()))


    def testLinearPipeline(self):
        source = GeneratorSource('s')
        source.inputs.gen.set_initial_packet(source_gen)
        shower = ShowInputs('printer')
        shower.inputs.add(InputPort('in1'))
        graph = Multigraph()
        graph.connect(source.outputs['OUT'], shower.inputs['in1'])
        graph()

    def testProductSource(self):
        source = components.GeneratorProductSource('s', source_gen, source_gen)
        shower = ShowInputs('printer')
        shower.inputs.add(InputPort('in1'))
        graph = Multigraph()
        graph.connect(source.outputs['OUT'], shower.inputs['in1'])
        graph()

    def testClose(self):
        with Multigraph() as g:
            producer = GeneratorSource('s1', (i for i in range(100)))
            constant = ConstantSource('const', 4)
            producer >> OutputPort('OUT')
            consumer = ShowInputs('printer')
            consumer << InputPort('IN')
            producer.outputs.OUT >> consumer.inputs.IN
        g()

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



    def testSplit(self):
        source1 = components.Product('s1', (i for i in range(3)),(i for i in range(3)),)
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
        toucher = pyperator.shell.Shell('shell', "touch {outputs.f1}")
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
        toucher = pyperator.shell.Shell('shell', "echo '{inputs.i.value}, {inputs.i.value} to {outputs.f1.path}' > {outputs.f1.path}")
        toucher.outputs.add(FilePort('f1'))
        toucher.inputs.add(InputPort('i'))
        toucher.DynamicFormatter('f1', "{inputs.i.value}.txt")
        printer = ShowInputs('show_path')
        printer.inputs.add(FilePort('f2'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, toucher.inputs.i)
        graph.connect(toucher.outputs.f1, printer.inputs.f2)
        graph()


    def testWildcardsFormatter(self):
        #Source
        source1 = GeneratorSource('s1', (i for i in range(5)))
        toucher = pyperator.shell.Shell('shell', "echo '{inputs.i.value}, {inputs.i.value} to {outputs.f1.path}' > {outputs.f1.path}")
        toucher.outputs.add(FilePort('f1'))
        toucher.inputs.add(InputPort('i'))
        toucher.DynamicFormatter('f1', "{inputs.i.value}.prova")
        #add transformation
        transformer = pyperator.shell.Shell('transf', "cp {inputs.IN.path} {outputs.out.path}")
        transformer.inputs.add(FilePort('IN'))
        transformer.outputs.add(FilePort('out'))
        transformer.WildcardsExpression('IN', "{value}.{ext}")
        transformer.DynamicFormatter('out', '{wildcards.IN.pane}.txt1')
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, toucher.inputs.i)
        graph.connect(toucher.outputs.f1, transformer.inputs.IN)
        graph()

    def testCombinatorialFormatter(self):
        #Source
        source1 = GeneratorSource('s1', (i for i in range(5)))
        source2 = GeneratorSource('s2', (i for i in range(5)))
        toucher = pyperator.shell.Shell('shell', "echo '{inputs.i.value}, {inputs.j.value}' > {outputs.f1.path}")
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
        toucher = pyperator.shell.Shell('shell', "cara")
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
        toucher = pyperator.shell.Shell('echo', "echo '{inputs.i} to {outputs.f1}' > {outputs.f1}")
        toucher.inputs.add(InputPort('i'))
        toucher.outputs.add(OutputPort('f1'))
        toucher.DynamicFormatter('f1', "{inputs.i}.txt")
        #Second component receives it
        modified = pyperator.shell.Shell('edit', "echo 'i saw {inputs.f1}' > {outputs.f2}")
        modified.inputs.add(InputPort('f1'))
        modified.outputs.add(OutputPort('f2'))
        modified.DynamicFormatter('f2', "{inputs.f1}.changes")
        #Finally we need a sink to drive the network
        printer = ShowInputs('show_path')
        printer.inputs.add(InputPort('f2'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, toucher.inputs.i)
        graph.connect(toucher.outputs.f1, modified.inputs.f1)
        graph.connect(modified.outputs.f2, printer.inputs.f2)
        graph()


    def testIIP(self):
        with Multigraph() as g:
            source1 = GeneratorSource('s1', (i for i in range(5)))
            printer = components.ShowInputs('print')
            printer << InputPort('i')
            printer << InputPort('j')
            #Add IIP to port
            printer.inputs.j.set_initial_packet('ciaone')
            #Connect remaining ports
            source1.outputs.OUT >> printer.inputs.i
            g()


    def testNiceConnection(self):
        with  Multigraph() as g:
            source1 = GeneratorSource('s1', (i for i in range(5)))
            source2 = GeneratorSource('s2', (i for i in range(5)))
            p = components.Product('prod')
            printer = components.ShowInputs('print')
            # #Add ports
            p << InputPort('i')
            p << InputPort('j')
            p >> OutputPort('OUT')
            printer << InputPort('IN')
            #Connect ports
            source1.outputs.OUT >> p.inputs.i
            source2.outputs.OUT >> p.inputs.j
            p.outputs.OUT >> printer.inputs.IN
            # # #Add components
            # g = g + source1 + source2 + p + printer
            print(g.dot())
        g()
        #Connect them

    def testConnectingToNonExisting(self):
        source1 = GeneratorSource('s1', (i for i in range(5)))
        source2 = GeneratorSource('s2', (i for i in range(5)))
        p = components.Product('prod')
        p << InputPort('i')
        p >> OutputPort('OUT')
        p.inputs.j
        source1.outputs.OUT >> p.inputs.i
        source2.outputs.OUT >> p.inputs.j



    def testProduct(self):
        source1 = GeneratorSource('s1', (i for i in range(5)))
        source2 = GeneratorSource('s2', (i for i in range(5)))
        p = components.Product('prod')
        printer = ShowInputs('printer')
        printer.inputs.add(InputPort('IN'))
        p.inputs.add(InputPort('i'))
        p.inputs.add(InputPort('j'))
        p.outputs.add(OutputPort('OUT'))
        g = Multigraph()
        g.connect(source1.outputs.OUT, p.inputs.i)
        g.connect(source2.outputs.OUT, p.inputs.j)
        g.connect(p.outputs.OUT, printer.inputs.IN)
        print(list(g.iterarcs()))
        print(g.dot())
        g()



    def testSubgraph(self):

        with subgraph.Subgraph('a') as sg:
            source1 = GeneratorSource('s1')
            source2 = GeneratorSource('s2',)
            p = components.Product('prod')
            p << InputPort('IN1')
            p << InputPort('IN2')
            source1.outputs.OUT >> p.inputs.IN1
            source2.outputs.OUT >> p.inputs.IN2
            sg.export_output(p.outputs.OUT)
            source1.inputs.gen.set_initial_packet(range(5))
            source2.inputs.gen.set_initial_packet(range(5))
        print(sg.dot())

        with Multigraph('b') as g:
            g.add_node(sg)
            printer  = components.ShowInputs('show')
            printer << InputPort('IN')
            sg.outputs.OUT >> printer.inputs.IN

        print('subgraph', g.dot())
        g()