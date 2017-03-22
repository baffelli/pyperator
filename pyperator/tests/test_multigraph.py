from unittest import TestCase

from ..DAG import  Multigraph
from ..components import GeneratorSource, ShowInputs, BroadcastApplyFunction
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
        source1 = GeneratorSource('s1',  (1 for i in range(100)))
        shower = ShowInputs('printer', inputs=['in1'])
        summer = BroadcastApplyFunction('summer', adder )
        summer.inputs.add(InputPort('g1'))
        summer.inputs.add(InputPort('recursion'))
        summer.outputs.add(OutputPort('sum'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, summer.inputs.g1)
        graph.connect(summer.outputs.sum, shower.inputs.in1)
        graph.connect(summer.outputs.sum, summer.inputs.recursion)
        graph.set_initial_packet(summer.inputs.recursion, 0)
        with open('/home/baffelli/recursion.dot','w+') as outfile:
            outfile.write(graph.dot())
        graph()






