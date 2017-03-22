from .nodes import Component
from .utils import Port, ArrayPort,InputPort, OutputPort
import asyncio

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





class ShowInputs(Component):

    def __init__(self, name, inputs=[]):
        super(ShowInputs, self).__init__(name)
        [self.inputs.add(InputPort(input)) for input in inputs]

    async def __call__(self):
        while True:
            data = await self.receive()
            print(data)
            # await asyncio.sleep(0)


