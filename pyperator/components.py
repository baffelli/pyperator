from .nodes import Component
from .utils import Port, ArrayPort,InputPort, OutputPort
import asyncio
import itertools

class GeneratorSource(Component):
    """
    This is a component that returns a single element from a generator
    to a single output
    """
    def __init__(self, name, generator, output='OUT'):
        super(GeneratorSource,self).__init__(name)
        self._gen = generator
        self.outputs.add(OutputPort(output))

    async def __call__(self):
        for g in self._gen:
            #We dont need to wait for incoming data
            data = {port_name: g for port_name, port in self.outputs.items()}
            await asyncio.wait(self.send(data))
            await asyncio.sleep(0)
        await self.close_downstream()


class ConstantSource(Component):
    """
    This is a component that continously outputs a constant to
    all the outputs, up to to :repeat: times, infinitely if :repeat: is none
    """
    def __init__(self, name, constant,outputs=['OUT'], repeat=None):
        super(ConstantSource, self).__init__(name)
        self.constant = constant
        self.repeat = repeat
        [self.outputs.add(OutputPort(output_name)) for output_name in outputs]

    async def __call__(self):
        for i in itertools.count():
            if self.repeat and i >= self.repeat:
                return
            else:
                data = {port_name: self.constant for port_name, port in self.outputs.items()}
                await asyncio.wait(self.send(data))
                await asyncio.sleep(0)


class Filter(Component):
    """
    This component filters the input according to the given predicate
    and sends it to the output
    """

    def __init__(self, name, predicate, **kwargs):
        super(Filter, self).__init__(name)
        self._predicate = predicate

    async def __call__(self):
        while True:
            data = await self.receive()
            filter_result = self._predicate(**data)
            #If the predicate is true, the data is sent
            if filter_result:
                data = {port_name: data for port_name, port in self.outputs.items()}
                await asyncio.wait(self.send(data))
            #otherwise nothing is sent and a message is sent  to
            #the components telling them that the filter failed
            else:
                continue


class BroadcastApplyFunction(Component):
    """
    This component applies a function of all inputs
    and sends it to all outputs
    """
    def __init__(self, name, function):
        super(BroadcastApplyFunction,self).__init__(name)
        self.function = function

    async def __call__(self):
        while True:
            data = await self.receive()
            transformed = self.function(**data)
            data = {port_name: transformed for port_name, port in self.outputs.items()}
            await asyncio.wait(self.send(data))
            await asyncio.sleep(0)



class ShowInputs(Component):

    def __init__(self, name, inputs=[]):
        super(ShowInputs, self).__init__(name)
        [self.inputs.add(InputPort(input)) for input in inputs]

    async def __call__(self):
        while True:
            data = await self.receive()
            print(data)
            await asyncio.sleep(0)


