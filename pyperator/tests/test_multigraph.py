from unittest import TestCase

from ..DAG import  Multigraph
from ..components import GeneratorSource, ShowInputs, BroadcastApplyFunction, ConstantSource, Filter, OneOffProcess
from .. import components
from ..nodes import Component
import asyncio
from ..utils import InputPort, OutputPort,ArrayPort


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
                [asyncio.ensure_future(c1.outputs['a'].send(m)), asyncio.ensure_future(c2.outputs['b'].send(m))]

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
        shower = ShowInputs('printer', inputs=['in1'])
        graph = Multigraph()
        graph.connect(source.outputs['OUT'], shower.inputs['in1'])
        graph.set_initial_packet(shower.inputs['in1'],5)

        graph()

    def testSumPipeline(self):
        source1 = GeneratorSource('s1',  (i for i in range(100)))
        source2 = GeneratorSource('s2',  (i for i in range(100)))
        shower = ShowInputs('printer', inputs=['in1'])
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
        source1 = GeneratorSource('s1',  (1 for i in range(1000)))
        shower = ShowInputs('printer', inputs=['in1'])
        summer = BroadcastApplyFunction('summer', adder )
        summer.inputs.add(InputPort('g1'))
        summer.inputs.add(InputPort('recursion'))
        summer.outputs.add(OutputPort('sum'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, summer.inputs.g1)
        graph.connect(summer.outputs.sum, shower.inputs.in1)
        graph.connect(summer.outputs.sum, summer.inputs.recursion)
        graph.set_initial_packet(summer.inputs.recursion, 1)
        with open('/home/baffelli/recursion.dot','w+') as outfile:
            outfile.write(graph.dot())
        graph()

    def testConstantSource(self):
        source1 = ConstantSource('s1', 3)
        shower = ShowInputs('printer', inputs=['in1'])
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
        shower = ShowInputs('printer', inputs=['a', 'b'])
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
        shower = ShowInputs('printer', inputs=['in1'])
        graph = Multigraph()
        graph.connect(source1.outputs['OUT'], filt.inputs.in1)
        graph.connect(filt.outputs.out1, shower.inputs.in1)
        graph()