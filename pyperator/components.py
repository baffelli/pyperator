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


class Split(Component):
    """
    This component splits the input tuple into
    separate ouputs; the number of elements is given
    with `n_outs`
    """
    def __init__(self, name, n_outs=2):
        super(Split, self).__init__(name)
        # [self.outputs.add(OutputPort('OUT{n}'.format(n=n))) for n in range(n_outs)]
        self.inputs.add(InputPort('IN'))


    async def __call__(self):
        while True:
            data = await self.receive()
            data = data.get('IN')
            out_data = {}
            for index_port, ((data_item),(output_port_name, output_port)) in enumerate(zip(data, self.outputs.items())):
                out_data[output_port_name] = data_item
            await asyncio.wait(self.send(out_data))
            await asyncio.sleep(0)



class GeneratorProductSource(Component):
    """
    This component returns a tuple obtained
    from a product of generators
    """
    pass



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
    This component computes a function of the inputs
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



class OneOffProcess(BroadcastApplyFunction):
    """
    This class awaits the upstream process once and then keeps on
    broadcasting the result to the outputs
    """
    def __init__(self, name, function):
        super(OneOffProcess,self).__init__(name, function)

    async def __call__(self):
        #wait once for the data
        data = await self.receive()
        while True:
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


class Shell(Component):
    """
    This component executes a shell script with inputs and outputs
    """
    def __init__(self, name, cmd):
        super(ShowInputs, self).__init__(name)



    def tofile(self):
        pass