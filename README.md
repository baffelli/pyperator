[![Travis](https://travis-ci.org/baffelli/pyperator.svg?branch=master)](https://travis-ci.org/baffelli/pyperator.svg?branch=master)

# Pyperator
Pyperator is a simple python workflow library based on asyncio. Freely inspired by other flow-based programming tools such as [noflo](https://noflojs.org/)
[scipipe](https://github.com/scipipe/scipipe/) and many [others](https://github.com/pditommaso/awesome-pipeline).
A network of components communicating through named ports is build; the execution happens asynchronously by scheduling all processes and sending/receving on the input/output ports.
## Simple example


A simple example workflow summing two numbers and printing the result can be built as follows:
```python
        from pyperator.DAG import  Multigraph
        from pyperator.components import GeneratorSource, ShowInputs, BroadcastApplyFunction, ConstantSource, Filter, OneOffProcess
        from pyperator import components
        from pyperator.nodes import Component
        from pyperator.utils import InputPort, OutputPort, FilePort, Wildcards
        #Sum function
        def adder(**kwargs):
                out = sum([item for k, item in kwargs.items() if item])
                return out
        #Create two source generating data from generator compherensions
        source1 = GeneratorSource('s1',  (i for i in range(100)))
        source2 = GeneratorSource('s2',  (i for i in range(100)))
        #Add a printer to display the result
        shower = ShowInputs('printer')
        #add input port
        shower.inputs.add(InputPort('in1'))
        #Function that applies a function of all input packets and sends it to all output ports
        summer = BroadcastApplyFunction('summer', adder )
        #Add ports
        summer.inputs.add(InputPort('g1'))
        summer.inputs.add(InputPort('g2'))
        summer.outputs.add(OutputPort('sum'))
        #Initialize DAG
        graph = Multigraph()
        #Connect ports
        graph.connect(source1.outputs.OUT, summer.inputs.g1)
        graph.connect(source2.outputs.OUT, summer.inputs.g2)
        graph.connect(summer.outputs.sum, shower.inputs.in1)
        #Execute dag
        graph()
```     
## How to use Pyperator

Creating a pyperator workflow requires three steps:
1. Define/import components
2. Define input/output ports 
3. create a graph by connecting ports

### Define components
Each pyperator component should be built subclassing `pyperator.nodes.Component`, which is in turn subclassed from the `AbstractComponent`, which has `__call__` as a abstract method. Your component should implement the `__call__` 
coroutine. An example of a simple component passing everything it receives from "IN" to "OUT":
```python
from pyperator import components
from pyperator.nodes import Component
from pyperator.utils import InputPort, OutputPort, FilePort, Wildcards
class PassThrough(Component):
    """
    This is a component that resends the same packets it receives
    """

    def __init__(self, name):
        super(PassThrough, self).__init__(name)
        self.inputs.add(InputPort("IN"))
        self.outputs.add(OutputPort("OUT"))

    @log_schedule
    async def __call__(self):
        while True:
                in_packets = await sefl.inputs.IN.receive()
                #this is critical, a packet has to be copied before
                #being sent again
                copied = in_packets.copy()
                await self.outputs.OUT.send_packet(copied)

```
To receive packets from a channel named "IN", you should use `packet = await self.inputs.IN.receive_packet()`. The input and output PortRegister support two forms of indexing:

* Selecting ports using dict-style keys, i.e `self.inputs["IN"]`

* Selecting them as attributes of the PortRegister, i.e `self.inputs.IN`

Likewise, sending packets is accomplished by issuing `await self.outputs.OUT.send(packet)`.

Now, we define a second components that creates some interesting packets. This component will be a source component, it will not have any input ports:
```python

```

### Define Input/Output Ports

There are two main ways to add ports to a component:

* Adding them when defining the component, using its __init__ method:

```python
class CustomComponent(Component):
    """
    This is my useless component
    """

    def __init__(self, name):
        super(CustomComponent, self).__init__(name)
        self._gen = generator
        self.outputs.add(OutputPort("OUT"))
        self.inputs.add(OutputPort("IN"))
```

* Adding ports to an existing compononent instance using the method `add` of the input and output PortRegister:

```python

c1 = CustomComponent("test")
#This component already has one input and output ports.
c1.inputs.add.InputPort("IN1")
c1.outputs.add.OutputPort("OUT1")

```
Now, c1 will have two `InputPort`s, "IN" and "IN1" and two `OutputPorts`"OUT" and "OUT1".

### Create a graph

Finally, several components can be tied together using a MultiGraph:
```python

```

### 

## Advanced example
```python
        from pyperator.DAG import  Multigraph
        from pyperator.components import GeneratorSource, ShowInputs, BroadcastApplyFunction, ConstantSource, Filter, OneOffProcess
        from pyperator import components
        from pyperator.nodes import Component
        from pyperator.utils import InputPort, OutputPort, FilePort, Wildcards
        #Source
        source1 = GeneratorSource('s1', (i for i in range(5)))
        source2 = GeneratorSource('s2', (i for i in range(5)))
        toucher = components.Shell('shell', "echo '{inputs.i.value}, {inputs.j.value}' > {outputs.f1.path}")
        toucher.outputs.add(FilePort('f1'))
        toucher.inputs.add(InputPort('i'))
        toucher.inputs.add(InputPort('j'))
        toucher.DynamicFormatter('f1', "{inputs.j.value}_{inputs.i.value}.txt1")
        printer = ShowInputs('show_path')
        printer.inputs.add(FilePort('f2'))
        graph = Multigraph()
        graph.connect(source1.outputs.OUT, toucher.inputs.i)
        graph.connect(source2.outputs.OUT, toucher.inputs.j)
        graph.connect(toucher.outputs.f1, printer.inputs.f2)
        graph()
```
