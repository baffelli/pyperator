from unittest import TestCase

from ..DAG import  Multigraph
from ..components import GeneratorSource
from ..nodes import Component
import asyncio


async def printer(**kwargs):
    print("Inputs are {}".format(kwargs))
    return

async def adder(**kwargs):
    out = {'result': sum([item for k, item in kwargs.items() if item])}
    return out


async def passer(**kwargs):
    await asyncio.sleep(0.2)
    print(kwargs)
    return {'delayed': kwargs.values()}

source_gen = (i for i in range(100))

class TestMultigraph(TestCase):


    def testConnet(self):
        c1 = Component('c1', outputs=['a','b'])
        c2 = Component('c2', inputs=['c', 'd'])
        graph = Multigraph()
        graph.connect(c1.outputs['a'], c2.inputs['c'])
        with open('/home/baffelli/out.dot','w+') as outfile:
            outfile.write(graph.dot())


    def testSendReceive(self):
        c1 = Component('c1', outputs=['a','b'])
        c2 = Component('c2', inputs=['c', 'd'])
        graph = Multigraph()
        graph.connect(c1.outputs['a'], c2.inputs['c'])
        graph.connect(c1.outputs['b'], c2.inputs['d'])
        graph.set_initial_packet(c2.inputs['c'], 6)
        async def send():
            await c1.outputs['a'].send('3')
        async def receive():
            res =await c2.inputs['c'].receive()
            print('done receiving')
            print(res)
        futures = [asyncio.ensure_future(send()),asyncio.ensure_future(receive())]
        loop = asyncio.get_event_loop()
        loop.run_until_complete((futures[1]))

    def testLinearPipeline(self):
        source = GeneratorSource('s', source_gen, outputs=['out1'])
        shower = Component('printer', inputs=['in1'], f= printer)
        graph = Multigraph()
        graph.connect(source.outputs['out1'], shower.inputs['in1'])
        graph.set_initial_packet(shower.inputs['in1'],5)
        graph()

    def testRecursivePipeline(self):
        source = GeneratorSource('s', source_gen, outputs=['out1'])
        shower = Component('printer', inputs=['in1'], f=printer)
        summer = Component('sum', inputs=['i','j'], outputs=['result'], f= adder)
        graph = Multigraph()
        graph.connect(source, summer, 'out1', 'i')
        graph.connect(summer, summer, 'out1', 'j')
        graph.connect(summer, shower,'result', 'in1' )
        graph()




