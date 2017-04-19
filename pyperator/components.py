import asyncio
import glob as _glob
import itertools as _iter
import subprocess as _sub

from .IP import  Bracket
from .exceptions import FormatterError, CommandFailedError, FileNotExistingError
from . import IP
from .nodes import Component
from .utils import InputPort, OutputPort, log_schedule, FilePort, Wildcards


class GeneratorSource(Component):
    """
    This is a component that returns a single element from a generator
    to a single output
    """

    def __init__(self, name, generator, output='OUT'):
        super(GeneratorSource, self).__init__(name)
        self._gen = generator
        self.outputs.add(OutputPort(output))

    @log_schedule
    async def __call__(self):
        async with self.outputs.OUT:
            for g in self._gen:
                await asyncio.wait(self.send_to_all(g))
                # await asyncio.sleep(0)


class GlobSource(Component):
    """
    This is a component that emits FilePackets
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
        start_message = "Component {}: using glob pattern {} will emit {} files: {}".format(self.name, pattern, len(files), files)
        self._log.info(start_message)
        for file in files:
            p = IP.FilePacket(file, owner=self)
            await self.outputs.OUT.send_packet(p)
            await asyncio.sleep(0)
        stop_message = "Component {}: exahusted list of files".format(self.name)
        self._log.info(stop_message)
        await self.close_downstream()


class Product(Component):
    """
    This component generates the
    cartesian product of the packets incoming from each ports and
    then sends them to the output port `OUT` as bracket IPs
    """

    def __init__(self, name):
        super().__init__(name)

    @log_schedule
    async def __call__(self):
        #Receive all packets
        all_packets = {k:[] for k in self.inputs.keys()}
        async for packet_dict in self.inputs:
            for port, packet in packet_dict.items():
                all_packets[port].append(packet)
        async with self.outputs.OUT:
            for it, p in enumerate(_iter.product(*all_packets.values())):
                #Create substream
                substream = [IP.OpenBracket()] + [p1.copy() for p1 in p] + [IP.CloseBracket()]
                #Send packets in substream
                for p1 in substream:
                    await self.outputs.OUT.send_packet(p1)
                await asyncio.sleep(0)


class FileListSource(Component):
    """
    This is a component that emits FilePackets
    from a list of files
    """

    def __init__(self, name, files):
        super(FileListSource, self).__init__(name)
        self.files = files
        self.outputs.add(FilePort('OUT'))

    @log_schedule
    async def __call__(self):
        for file in self.files:
            p = IP.FilePacket(file, owner=self)
            await self.outputs.OUT.send_packet(p)
            await asyncio.sleep(0)
        await self.close_downstream()


class ReplacePath(Component):
    """
    This is a component that emits FilePackets
    with a path obtained by replacing the input path
    """

    def __init__(self, name, pattern):
        super(ReplacePath, self).__init__(name)
        self.pattern = pattern
        self.inputs.add(FilePort('IN'))
        self.outputs.add(FilePort('OUT'))

    @log_schedule
    async def __call__(self):
        while True:
            p = await self.inputs.IN.receive_packet()
            p1 = IP.FilePacket(p.path.replace(*self.pattern), owner=self)
            p.drop()
            await self.outputs.OUT.send_packet(p1)
            await asyncio.sleep(0)


class PathToFilePacket(Component):
    """
    This component converts a path to a file packet
    """
    pass


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
        #Iterate over input stream
        async for packet in self.inputs.IN:
            if isinstance(packet, IP.OpenBracket):
                packet.drop()
                data = []
            elif isinstance(packet, IP.CloseBracket):
                packet.drop()
                self._log.debug(
                    "Component {}: Splitting '{}'".format(self.name, data))
                for (output_port_name, output_port), out_packet in zip(self.outputs.items(), data):
                    await output_port.send_packet(out_packet.copy())
            else:
                data.append(packet)
                await asyncio.sleep(0)


class IterSource(Component):
    """
    This component returns a Bracket IP
    from a itertool function such as product
    """

    def __init__(self, name, *generators, function=_iter.product):
        super(IterSource, self).__init__(name)
        self.generators = generators
        self.outputs.add(OutputPort('OUT'))
        self.function = function

    @log_schedule
    async def __call__(self):
        for items in self.function(*self.generators):
            open = IP.OpenBracket()
            await self.outputs.OUT.send_packet(open)
            for item in items:
                packet = IP.InformationPacket(item)
                await self.outputs.OUT.send_packet(packet)
            await self.outputs.OUT.send_packet(IP.CloseBracket())
        await asyncio.sleep(0)
        await self.close_downstream()


class ConstantSource(Component):
    """
    This is a component that continously outputs a constant to
    all the outputs, up to to :repeat: times, infinitely if :repeat: is none
    """

    def __init__(self, name, constant, outputs=['OUT'], repeat=None):
        super(ConstantSource, self).__init__(name)
        self.constant = constant
        self.repeat = repeat
        [self.outputs.add(OutputPort(output_name)) for output_name in outputs]

    def type_str(self):
        return "constant {}".format(self.constant)

    @log_schedule
    async def __call__(self):
        for i in _iter.count():
            if self.repeat and i >= self.repeat:
                return
            else:
                # packet = IP.InformationPacket
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

    @log_schedule
    async def __call__(self):
        while True:
            data = await self.receive()
            filter_result = self._predicate(**data)
            # If the predicate is true, the data is sent
            if filter_result:
                data = {port_name: data for port_name, port in self.outputs.items()}
                await asyncio.wait(self.send_to_all(filter_result))
            # otherwise nothing is sent and a message is sent  to
            # the components telling them that the filter failed
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

class FileOperator(Component):
    """
    This component operates on files, it supports
    wilcard expressions and output file formatters based on
    input files, i.e extracting part of the paths to generate output paths
    """
    def __init__(self, name):
        super(FileOperator, self).__init__(name)
        self.output_formatters = {}
        # Input ports may have wildcard expressions attached
        self.wildcard_expressions = {}


    def FixedFormatter(self, port, path):
        """
        Formats the ouput port with a fixed

        """
        self.output_formatters[port] = lambda inputs, outputs, wildcards: path

    def DynamicFormatter(self, outport, pattern):
        self.output_formatters[outport] = lambda inputs, outputs, wildcards: pattern.format(inputs=inputs,
                                                                                            outputs=outputs,
                                                                                            wildcards=wildcards)

    def WildcardsExpression(self, inport, pattern):
        self.wildcard_expressions[inport] = Wildcards(pattern)

    def parse_wildcards(self, received_data):
        """
        This function parses the input packets
        to extract the wildcards, if any are defined.
        Returns a dict of wildcards objects
        which can be accessed as
        {portname.wildcards.wildcard_name}
        """
        wildcards_dict = {}
        for inport, inpacket in received_data.items():
            if inport in self.wildcard_expressions:
                wildcards_dict[inport] = self.wildcard_expressions[inport].parse(inpacket.path)
                self._log.debug(
                    'Component {}: Port {}, with wildcard pattern {}, wildcards are {}'.format(self.name, inport,
                                                                                               self.wildcard_expressions[
                                                                                                   inport].pattern,
                                                                                               wildcards_dict[inport]))
        wildcards = type('wildcards', (object,), wildcards_dict)
        return wildcards

    def generate_output_paths(self, received_data):
        """
        This function generates the (dynamic) output and inputs
        paths using the inputs and the formatting functions
        """

        inputs = type('inputs', (object,), received_data)
        out_paths = {}
        wildcards = self.parse_wildcards(received_data)
        for out, out_port in self.outputs.items():
            try:
                # First try formatting outpur
                out_paths[out] = self.output_formatters[out](inputs, out_paths, wildcards)
                self._log.debug(
                    "Component {}: Output port {} will send file '{}'".format(self.name, out_port, out_paths[out]))
            except NameError as e:
                ex_text = 'Component {}: Port {} does not have a path formatter specified'.format(self.name, out)
                self._log.error(ex_text)
                raise FormatterError(ex_text)
            except Exception as e:
                print(e)
        return out_paths, wildcards

    def generate_packets(self, out_paths):
        out_packets = {}
        for port, path in out_paths.items():
            out_packets[port] = IP.FilePacket(path)
        return out_packets

    def enumerate_missing(self, out_packets):
        return {port: packet for port, packet in out_packets.items() if not packet.exists}


    def produce_outputs(self, input_packets, output_packets, wildcards):
        pass



    @log_schedule
    async def __call__(self):
        while True:
            # Wait for all upstram to be completed
            received_packets = await self.receive_packets()
            print(received_packets)
            # Generate output paths
            out_paths, wildcards = self.generate_output_paths(received_packets)
            out_packets = self.generate_packets(out_paths)
            # Check for missing packet
            missing = self.enumerate_missing(out_packets)
            if missing:
                self._log.debug(
                    "Component {}: Output files '{}' do not exist not exist, command will be run".format(self.name,
                                                                                                         [
                                                                                                             packet.path
                                                                                                             for
                                                                                                             packet
                                                                                                             in
                                                                                                             missing.values()]))
                inputs_obj = type('a', (object,), received_packets)
                ouputs_obj = type('a', (object,), out_packets)
                # Produce the outputs
                out_packets = self.produce_outputs(inputs_obj, ouputs_obj, wildcards)
                # Check if the output files exist
                missing_after = self.enumerate_missing(out_packets)
                if missing_after:
                    missing_err = "Component {name}: Following files are missing {}, check the command".format(
                        self.name, [packet.path for packet in missing_after.values()])

                    self._log.error(missing_err)
                    raise FileNotExistingError(missing_err)
            else:
                self._log.info(
                    "Component {}: All output files exist, command will not be run".format(self.name))
            await asyncio.wait(self.send_packets(out_packets))
            await asyncio.sleep(0)



class Shell(FileOperator):
    """
    This component executes a shell script with inputs and outputs
    the command can contain normal ports and FilePorts
    for input and output
    """

    def __init__(self, name, cmd):
        super(Shell, self).__init__(name)
        self.cmd = cmd
        self.output_formatters = {}
        # Input ports may have wildcard expressions attached
        self.wildcard_expressions = {}

    def produce_outputs(self, input_packets, output_packets, wildcards):
        formatted_cmd = self.cmd.format(inputs=input_packets, outputs=input_packets, wildcards=wildcards)
        self._log.debug("Executing command {}".format(formatted_cmd))
        # Define stdout and stderr pipes
        stdout = _sub.PIPE
        stderr = _sub.PIPE
        proc = _sub.Popen(formatted_cmd, shell=True, stdout=stdout, stderr=stderr)
        stdoud, stderr = proc.communicate()
        if proc.returncode != 0:
            fail_str = "running command '{}' failed with output: \n {}".format(formatted_cmd, stderr.strip())
            ext_str = "Component {}: ".format(self.name, ) + fail_str
            e = CommandFailedError(self, fail_str)
            self._log.error(e)
            raise e
        else:
            success_str = "Component {}: command successfully run, with output: {}".format(self.name, stdout)
            self._log.info(success_str)
            return output_packets


