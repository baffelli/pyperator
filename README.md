# Pyperator
Pyperator is a simple python workflow library based on asyncio. Freely inspired by other flow-based programming tools such as [noflo](https://noflojs.org/)
[scipipe](https://github.com/scipipe/scipipe/) and many [others](https://github.com/pditommaso/awesome-pipeline).
A network of components communicating through named ports is build; the execution happens asynchronously by scheduling all processes and sending/receving on the input/output ports.
## Simple example
A simple example workflow can be built as follows:
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
