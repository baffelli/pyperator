import asyncio
import subprocess as _sub

from pyperator import IP
from pyperator.exceptions import FormatterError, FileNotExistingError, CommandFailedError
from pyperator.nodes import Component
from pyperator.utils import Wildcards, log_schedule

import collections.abc as _collabc

import hashlib as _hl


def unique_filename(outport, inputs, wildcards):
    unique_if = ("".join([str(v.path) for p,v in inputs.items()])).encode('utf-8')
    return str(_hl.md5(unique_if).hexdigest())



class Inputs(_collabc.Mapping):
    """
    This class is used to represent the
    node inputs so that each input
    is accessible as an attribute
    """

    def __init__(self, received_packets):
        self._inputs = received_packets

    def __getattr__(self, item):
        return self[item]

    def __getitem__(self, item):
        if item in self._inputs:
            return self._inputs.get(item)
        else:
            pass

    def __iter__(self):
        return self._inputs.__iter__()

    def __len__(self):
        print(self._inputs)
        return len(self._inputs)


class Outputs(Inputs):

    def __init__(self, received_packets):
        super().__init__(received_packets)





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
        self.output_formatters[port] = lambda inputs, wildcards: path

    def DynamicFormatter(self, outport, pattern):
        self.output_formatters[outport] = lambda inputs, wildcards: pattern.format(inputs=inputs,
                                                                                            wildcards=wildcards)
    def UniqueFormatter(self, outport):
        formatter = lambda inputs, wildcards: unique_filename(outport,inputs, wildcards)
        self.output_formatters[outport] = formatter

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

        inputs = Inputs(received_data)
        out_paths = {}
        wildcards = self.parse_wildcards(received_data)
        for out, out_port in self.outputs.items():
            try:
                # First try formatting outpur
                try:
                    out_paths[out] = self.dag.workdir + self.output_formatters[out](inputs, wildcards)
                except KeyError:
                    out_paths[out] = self.UniqueFormatter(out)(inputs, wildcards)
                    self._log.info("Component {}: Output port {} has no output formatter specified, will form an unique ID based on inputs".format(self.name, out_port, out_paths[out]))
                self._log.debug(
                    "Component {}: Output port {} will send file '{}'".format(self.name, out_port, out_paths[out]))
            except NameError as e:
                ex_text = 'Component {}: Port {} does not have a path formatter specified'.format(self.name, out)
                self._log.error(ex_text)
                raise FormatterError(ex_text)
            except Exception as e:
                raise e
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
                inputs_obj = Inputs(received_packets)
                outputs_obj = Outputs(out_packets)
                # Produce the outputs
                out_packets = self.produce_outputs(inputs_obj, outputs_obj, wildcards)
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
        formatted_cmd = self.cmd.format(inputs=input_packets, outputs=output_packets, wildcards=wildcards)
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