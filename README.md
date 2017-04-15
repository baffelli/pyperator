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
coroutine. An example of a simple component summing the content of the packets received in "IN1" and "IN2":
```python
from pyperator import components
from pyperator.nodes import Component
from pyperator.utils import InputPort, OutputPort, FilePort, Wildcards
from pyperator.IP import InformationPacket
from pyperator.DAG import  Multigraph
import asyncio
import random

class Summer(Component):
    """
    This is a component that sums the value of the recieved packets
    """

    def __init__(self, name):
        super(Summer, self).__init__(name)
        self.inputs.add(InputPort("IN1"))
        self.inputs.add(InputPort("IN2"))
        self.outputs.add(OutputPort("OUT"))

    @log_schedule
    async def __call__(self):
        while True:
                in_packets_1 = await sefl.inputs.IN1.receive()
                in_packets_2 = await sefl.inputs.IN1.receive()
                #InformationPackets have the attribute "value" that contains the data
                summed = InformatioPacket(in_packets_1.value() + in_packets_2.value())
                await self.outputs.OUT.send_packet(summed)

```
To receive packets from a channel named "IN", you should use `packet = await self.inputs.IN.receive_packet()`. The input and output PortRegister support two forms of indexing:

* Selecting ports using dict-style keys, i.e `self.inputs["IN"]`

* Selecting them as attributes of the PortRegister, i.e `self.inputs.IN`

Likewise, sending packets is accomplished by issuing `await self.outputs.OUT.send(packet)`.

Now, we define a second components that creates some interesting packets. This component will be a source component, it will not have any input ports and will generate packtes consisting of random numbers:
```python
class RandomSource(Component):
        """
        This component generates random packets
        """
        def __init__(self, name):
                super(RandomSource, self).__init__(name)
                self.name = name
                self.outputs.add(OutputPort("OUT"))
                
        async def __call__(self):
                while True:
                        #generate IP containing random number
                        a = InformationPacket(random.random())
                        #send to the output port
                        await self.outputs.OUT.send_packet(a)
                        await asyncio.sleep(0)


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
this is what we have done before to define the `Summer` and the `RandomSource`components.
* Adding ports to an existing compononent instance using the method `add` of the input and output PortRegister:

```python

c1 = CustomComponent("test")
#This component already has one input and output ports.
c1.inputs.add.InputPort("IN1")
c1.outputs.add.OutputPort("OUT1")

```
Now, c1 will have two `InputPort`s, "IN" and "IN1" and two `OutputPorts`"OUT" and "OUT1".

### Create a graph

Finally, several components can be tied together using a MultiGraph. In this case, we want to compute the sum of two random packets and print the result. To print the result we import the `ShowInputs` component from `pyperator.components` that will print the packet it receives from each port.
```python

#Define a graph
g = Multigraph()

#Instantiate components

s1 = RandomSource("s1")
s2 = RandomSource("s2")
adder = Summer("sum_them")
printer = ShowInputs("show_it")
#The printer needs an input port
printer.inputs.add(InputPort("IN"))

#Now we connect the components

s1.outputs.OUT.connect(adder.inputs.IN1)
s2.outputs.OUT.connect(adder.inputs.IN2)
adder.outputs.OUT.connect(printer.inputs.IN)

#Now we need to add them to a Graph instance to be able to run them.

g.add_node(s1)
g.add_node(s2)
g.add_node(adder)
g.add_node(printer)

#We can vrun the computation by calling the graph
g()

```

### Create a graph using magic methods
Pyperator also supports a nicer syntax to express graphs and connect ports. The same graph of the previous example can be expressed
in a more suggestive way using:

```python

#all nodes defined within this context manager will be automatically be added to the graph `g`
with Multigraph() as g:
        s1 = RandomSource("s1")
        s2 = RandomSource("s2")
        adder = Summer("sum_them")
        printer = ShowInputs("show_it")
        #The printer needs an input port
        printer.inputs.add(InputPort("IN"))
        #Connect 
        s1.outputs.OUT >> adder.inputs.IN1
        s2.outputs.OUT >> adder.inputs.IN2
        adder.outputs.OUT >> printer.inputs.IN
        
g()
        
        
```

### 

## Advanced example
In this example we will see how pyperator supports shell commands and files, including wildcards and the generation of dynamic filenames. Many of these features are inspired by [scipipe](https://github.com/scipipe/scipipe/).
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
