from .nodes import Component
import asyncio

class GeneratorSource(Component):
    """
    This is a component that returns a single element from a generator
    to a single output
    """
    def __init__(self, name, generator, outputs=[]):
        super(GeneratorSource,self).__init__(name, generator, inputs=[], outputs=outputs)
        self._gen = generator

    async def __call__(self):
        #We dont need to wait for incoming data
        gen_output = next(self._gen)
        print(gen_output)
        #We call the generator and send
        transformed = {out_name: gen_output for out_name, out_port in self.outports}
        await self.send(transformed)
        for out, con in self.outports:
            asyncio.ensure_future(con._connection.dest())
        await asyncio.sleep(0)





class GeneratorProductSource(Component):
    """
    This is a component that returns
    the product of the given generators
    """


class Sink(Component):
    pass