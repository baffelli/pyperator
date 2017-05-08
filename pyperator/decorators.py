
from pyperator.utils import InputPort, OutputPort
from pyperator.nodes import Component
from pyperator.exceptions import NotCoroutineError
from functools import wraps
from pyperator.DAG import Multigraph
from pyperator.subnet import SubIn
import asyncio






def log_schedule(method):
    def inner(instance):
        try:
            instance.log.info('Component {}: Scheduled'.format(instance.name))
        except AttributeError:
            pass
        return method(instance)

    return inner


def run_once(func):
    """
    Using this decorator, any 
    :class:`pyperator.nodes.components` instance
    will be made to run exactly once the first
    time all of its inputs will be present. This is
    acheived by wrapping a component in a subnet
    """
    @wraps(func)
    def inner(*args, **kwargs):
        #Add a graph

        comp = func(*args, **kwargs)
        g = Multigraph(comp.name+'_'+'wrapper')
        g.add_node(comp)
        #For each port, add
        #an "once" component
        for (in_name, in_port) in comp.inputs.items():
            in_node = SubIn('IN_'+in_name)
            once_node = Once('once_'+in_name)
            g.add_node(in_node)
            g.add_node(once_node)
            #Connect
            in_node.outputs.OUT.connect(once_node.inputs.IN)
            once_node.outputs.OUT.connect(in_port)
            #Export inputs
            g.inputs.export(in_node.inputs.IN, in_name)
        #Export outputs
        for (out_name, out_port) in comp.outputs.items():
            g.outputs.export(out_port, out_name)
        return g
    return inner



def repeat_out(port_name):
    """
    Using this decorator, 
    :class:`pyperator.nodes.components` the output
    at the specified `port_name` will be repeated forever.
    This is useful in combination with :py:meth:`pyperator.decorators.run_once`, 
    if a long running process should have its output repeated
    forever without the processing being rerun continously.
    
    :param port_name: 
    :return: 
    """
    def inner(func):
        @wraps(func)
        def second_level(*args, **kwargs):
            comp = func(*args, **kwargs)
            g = Multigraph(comp.name + '_' + 'wrapper')
            g.add_node(comp)




def component(func):
    """
    Using this decorator, any coroutine_
    function can be turned into a :class:`pyperator.nodes.components` component.
    The function should take an argument only, whose attribute will be `inputs`,
    `outputs` and `log`.
    
    :param func: coroutine function
    :return: 
    
    .. _coroutine: https://docs.python.org/3/library/asyncio-task.html
    """
    if  asyncio.iscoroutinefunction(func):
        def inner(*args, **kwargs):
            new_c = type(func.__name__,(Component,), {'__call__':func, "__doc__":func.__doc__})
            return new_c(*args, **kwargs)
        return inner
    else:
        raise NotCoroutineError(func)




def inport(portname,**portopts):
    def inner_dec(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            c1 = func(*args, **kwargs)
            c1.inputs.add(InputPort(portname,**portopts))
            return c1
        return wrapper
    return inner_dec

def outport(portname,**portopts):
    def inner_dec(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            c1 = func(*args, **kwargs)
            c1.outputs.add(OutputPort(portname,**portopts))
            return c1
        return wrapper
    return inner_dec


@outport('OUT')
@inport('IN')
@component
async def Once(self):
    """
    This component 
    receives from `IN` once and sends
    the result to `OUT`. Afterwards, it closes
    :param self: 
    :return: 
    """
    in_packet = await self.inputs.IN.receive_packet()
    await self.outputs.OUT.send_packet(in_packet.copy())
    await self.inputs.IN.close()