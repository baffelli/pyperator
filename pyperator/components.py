from .nodes import Component
from .utils import Port, ArrayPort,InputPort, OutputPort, Wildcards
import asyncio
import itertools
from collections import namedtuple as _nt
from . import IP

import subprocess as _sub


import logging

class FormatterError(Exception):
    pass

class FileExistsException(Exception):
    pass

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
            await asyncio.wait(self.send_to_all(g))
            await asyncio.sleep(0)
        await self.close_downstream()



class Split(Component):
    """
    This component splits the input tuple into
    separate ouputs; the number of elements is given
    with `n_outs`
    """
    def __init__(self, name):
        super(Split, self).__init__(name)
        # [self.outputs.add(OutputPort('OUT{n}'.format(n=n))) for n in range(n_outs)]
        self.inputs.add(InputPort('IN'))


    async def __call__(self):
        while True:
            data = await self.inputs.IN.receive()
            for index_port, ((data_item),(output_port_name, output_port)) in enumerate(zip(data, self.outputs.items())):
                asyncio.ensure_future(output_port.send(data_item))
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
                await asyncio.wait(self.send_to_all(self.constant))
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
                await asyncio.wait(self.send_to_all(filter_result))
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
            self.send_to_all(transformed)
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
            data = transformed
            await asyncio.wait(self.send_to_all(data))
            await asyncio.sleep(0)


class ShowInputs(Component):

    def __init__(self, name):
        super(ShowInputs, self).__init__(name)

    async def __call__(self):
        while True:
            packets = await self.receive_packets()
            # st = " ".join(["From {port}: {p.value}".format(port=port, p=packet) for port, packet in packets.items()])
            # print(st)
            # print(map("{p.value}".format(p=packets)))
            await asyncio.sleep(0)


class Shell(Component):
    """
    This component executes a shell script with inputs and outputs
    the command can contain normal ports and FilePorts
    for input and output
    """
    def __init__(self, name, cmd):
        super(Shell, self).__init__(name)
        self.cmd = cmd
        #
        self.output_formatters = {}

    def FixedFormatter(self, port, path):
        self.output_formatters[port] = lambda data: path

    def DynamicFormatter(self, outport, pattern):
        self.output_formatters[outport] = pattern


    def format_paths(self, received_data):
        """
        This function generates the (dynamic) output and inputs
        paths using the inputs and the formatting functions
        """

        inputs = type('inputs', (object,), received_data)
        outputs = {}
        packets = {}
        existing = False
        for out, out_port in self.outputs.items():
            try:
                outputs[out] = self.output_formatters[out].format(inputs=inputs, outputs=outputs)
                logging.getLogger('root').debug("{}: Output port {} will produce file '{}'".format(self.name, out_port, outputs[out]))
                packets[out] = IP.FilePacket(outputs[out])
                #If any file with the same name exists
                if packets[out].exists:
                    logging.getLogger('root').debug("{}: Output file '{}' exist".format(self.name, packets[out].path))
                    existing = True
            except Exception as e:
                raise FormatterError('Port {} does not have a path formatter specified'.format(out))
        outputs = type('outputs', (object,), packets)
        return inputs, outputs, packets, existing


    async def __call__(self):
        while True:
            #Wait for all upstram to be completed
            received_packets = await self.receive_packets()
            #If the packet exists, we skip
            inputs, outputs, packets , existing = self.format_paths(received_packets)
            if not existing:
                formatted_cmd = self.cmd.format(inputs=inputs, outputs=outputs)
                logging.getLogger('root').debug("Executing command {}".format(formatted_cmd))
                #Run subprocess
                proc = _sub.Popen(formatted_cmd, shell=True)
            else:
                logging.getLogger('root').debug("{}: Skipping command because output files exist".format(self.name))
            await asyncio.wait(self.send_packets(packets))
            await asyncio.sleep(0)




