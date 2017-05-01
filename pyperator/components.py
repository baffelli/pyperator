import asyncio
import glob as _glob
import itertools as _iter
import pathlib as _path

from pyperator import IP
from pyperator.nodes import Component
from pyperator.utils import InputPort, OutputPort, FilePort
from pyperator.decorators import log_schedule


class GeneratorSource(Component):
    """
    This is a component that returns a single element from a generator
    passed at initalization time to 'gen'
    to a single output 'OUT'
    """

    def __init__(self, name):
        super(GeneratorSource, self).__init__(name)
        self.outputs.add(OutputPort('OUT'))
        self.inputs.add(InputPort('gen'))

    @log_schedule
    async def __call__(self):
        gen = await self.inputs.gen.receive()
        async with self.outputs.OUT:
            for g in gen:
                await asyncio.wait(self.send_to_all(g))
                # await asyncio.sleep(0)


class GlobSource(Component):
    """
    This is a component that emits Packets
    according to a glob pattern specified
    when the component is initialized
    """

    def __init__(self, name):
        super(GlobSource, self).__init__(name)
        self.outputs.add(FilePort('OUT'))
        self.inputs.add(InputPort('pattern'))

    @log_schedule
    async def __call__(self):
        pattern = await self.inputs.pattern.receive()
        files = _glob.glob(pattern)
        start_message = "using glob pattern {} will emit {} files: {}".format(pattern, len(files), files)
        self.log.info(start_message)
        for file in files:
            p = IP.InformationPacket(_path.Path(file), owner=self)
            await self.outputs.OUT.send_packet(p)
            await asyncio.sleep(0)
        stop_message = "exahusted list of files"
        self._log.info(stop_message)
        await self.close_downstream()


class Product(Component):
    """
    This component generates the
    cartesian product of the packets incoming from each ports and
    then sends them to the output port `OUT` as bracket IPs.
    Alternatively, by providing a function `fun` to the constructor, another
    combinatorial function can be used to generate the packets.
    """

    def __init__(self, name, fun=lambda packets: _iter.product(*packets)):
        super().__init__(name)
        self._fun = fun
        self.outputs.add(OutputPort('OUT'))

    @log_schedule
    async def __call__(self):
        # Receive all packets
        all_packets = {k: [] for k in self.inputs.keys()}
        async for packet_dict in self.inputs:
            for port, packet in packet_dict.items():
                all_packets[port].append(packet)
        async with self.outputs.OUT:
            for it, p in enumerate(self._fun(all_packets.values())):
                # Create substream
                substream = [IP.OpenBracket()] + [p1.copy() for p1 in p] + [IP.CloseBracket()]
                # Send packets in substream
                for p1 in substream:
                    await self.outputs.OUT.send_packet(p1)
                await asyncio.sleep(0)


class FileListSource(Component):
    """
    This is a component that emits InformationPackets
    from a list of files
    """

    def __init__(self, name, files):
        super(FileListSource, self).__init__(name)
        self.files = files
        self.outputs.add(FilePort('OUT'))

    @log_schedule
    async def __call__(self):
        for file in self.files:
            p = IP.InformationPacket(file, owner=self)
            await self.outputs.OUT.send_packet(p)
            await asyncio.sleep(0)
        await self.close_downstream()


class ReplacePath(Component):
    """
    This is a component that emits InformationPackets
    with a path obtained by replacing the input path
    """

    def __init__(self, name, pattern):
        super(ReplacePath, self).__init__(name)
        self.inputs.add(InputPort('IN'))
        self.inputs.add(InputPort('pattern'))
        self.outputs.add(OutputPort('OUT'))

    @log_schedule
    async def __call__(self):
        pattern = await self.inputs.pattern.receive()
        while True:
            p = await self.inputs.IN.receive_packet()
            p1 = IP.InformationPacket(p.path.replace(*self.pattern), owner=self)
            p.drop()
            await self.outputs.OUT.send_packet(p1)
            await asyncio.sleep(0)


class Split(Component):
    """
    This component splits the input tuple into
    separate ouputs; the number of elements is given
    with `n_outs`
    """

    def __init__(self, name):
        super(Split, self).__init__(name)
        self.inputs.add(InputPort('IN'))

    @log_schedule
    async def __call__(self):
        # Iterate over input stream
        async for packet in self.inputs.IN:
            if isinstance(packet, IP.OpenBracket):
                packet.drop()
                data = []
            elif isinstance(packet, IP.CloseBracket):
                packet.drop()
                self._log.debug(
                    "Splitting '{}'".format(data))
                for (output_port_name, output_port), out_packet in zip(self.outputs.items(), data):
                    await output_port.send_packet(out_packet.copy())
            else:
                data.append(packet)
                await asyncio.sleep(0)


# class IterSource(Component):
#     """
#     This component returns a Bracket IP
#     from a itertool function such as product
#     """
#
#     def __init__(self, name, *generators, function=_iter.combinations):
#         super(IterSource, self).__init__(name)
#         self.generators = generators
#         self.outputs.add(OutputPort('OUT'))
#         self.function = function
#
#     @log_schedule
#     async def __call__(self):
#         for items in self.function(*self.generators):
#             open = IP.OpenBracket()
#             await self.outputs.OUT.send_packet(open)
#             for item in items:
#                 packet = IP.InformationPacket(item)
#                 await self.outputs.OUT.send_packet(packet)
#             await self.outputs.OUT.send_packet(IP.CloseBracket())
#         await asyncio.sleep(0)
#         await self.close_downstream()


class ConstantSource(Component):
    """
    This is a component that continously outputs a constant to
    the output 'OUT', up to to :repeat: times, infinitely if :repeat: is none
    The constant is given to the 'constant' port
    """

    def __init__(self, name):
        super(ConstantSource, self).__init__(name)
        self.outputs.add(OutputPort('OUT'))
        self.outputs.add(InputPort('constant'))
        self.outputs.add(InputPort('repeat'))

    @log_schedule
    async def __call__(self):
        repeat = await self.inputs.repeat.receive()
        constant = await self.inputs.constant.receive()
        for i in _iter.count():
            if repeat and i >= repeat:
                return
            else:
                # packet = IP.InformationPacket
                await asyncio.wait(self.send_to_all(constant))
                await asyncio.sleep(0)


class Repeat(Component):
    """
    This component receives
    from his input once only
    and keeps on repeating
    it on the output
    """

    def __init__(self, name):
        super(Repeat, self).__init__(name)
        self.inputs.add(InputPort('IN'))
        self.outputs.add(OutputPort('OUT'))

    async def __call__(self):
        packet = await self.inputs.IN.receive_packet()
        self.inputs.IN.close()
        with self.outputs.OUT:
            while True:
                self.outputs.OUT.send_packet(packet.copy())


class Filter(Component):
    """
    This component filters the input in 'IN' according to the given predicate in the port 'predicate'
    and sends it to the output 'OUT' if the predicate is true
    """

    def __init__(self, name):
        super(Filter, self).__init__(name)
        self.inputs.add(InputPort('IN'))
        self.inputs.add(InputPort('predicate'))
        self.outputs.add(OutputPort('OUT'))

    @log_schedule
    async def __call__(self):
        predicate = self.inputs.predicate.receive()
        while True:
            data = await self.IN.receive()
            filter_result = predicate(data)
            # If the predicate is true, the data is sent
            if filter_result:
                await self.outputs.OUT.send(data)
            else:
                continue


class BroadcastApplyFunction(Component):
    """
    This component computes a function of the inputs
    and sends it to all outputs
    """

    def __init__(self, name, function):
        super(BroadcastApplyFunction, self).__init__(name)
        self.function = function

    @log_schedule
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
        super(OneOffProcess, self).__init__(name, function)

    @log_schedule
    async def __call__(self):
        # wait once for the data
        data = await self.receive()
        while True:
            transformed = self.function(**data)
            data = transformed
            await asyncio.wait(self.send_to_all(data))
            await asyncio.sleep(0)


class ShowInputs(Component):
    def __init__(self, name):
        super(ShowInputs, self).__init__(name)

    @log_schedule
    async def __call__(self):
        while True:
            packets = await self.receive_packets()
            show_str = "Component {} saw:\n".format(self.name) + "\n".join([str(p) for p in packets.values()])
            self._log.debug(show_str)
            print(show_str)
