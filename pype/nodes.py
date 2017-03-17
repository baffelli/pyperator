from pype.utils import messageList, channel
import asyncio

class Node:
    def __init__(self, name, f=lambda x: None):
        self.name = name
        self._data = None
        self._in = set()
        self._out = set()
        self.channel = channel(name='c', owner=self, dest=None)
        self.f = f
        self.data = set()
        self.color = 'grey'
        try:
            self.chan = self.f()
        except TypeError:
            pass

    def __repr__(self):
        st = "{}".format(self.name)
        return st

    def gv_node(self):
        st = "{name} [fillcolor={c}, label=\"{name}\", style=filled]".format(c=self.color, name=str(self))
        return st

    def add_outgoing(self, node):
        if not node in self._out:
            self._out.add(node)

    def add_incoming(self, node):
        # Find channels
        if not node in self._in:
            self._in.add(node)

    def remove_outgoing(self, node):
        self._out.pop(node)

    def remove_incoming(self, node):
        self._in.pop(node)

    def find_channel(self, node):
        c = [c for c in self._channels if c.connection_exists(self, node)] + [c for c in node._channels if
                                                                              c.connection_exists(self, node)]
        return c[0]


    async def get_upstream(self):
        data = []
        if self.n_in > 0:
            for incoming_node  in self.incoming:
                print("{}, receiving on {}".format(self.name, incoming_node))
                current_data = await self.channel.receive()
                old_name = self.name
                data = (old_name, current_data)
                self.data.add(data)
                return
                # print("{}, received {}".format(self.name, current_data))
                # incoming_node().send(None)
        return data

    async def send_downstream(self, data):
        if self.n_out > 0:
            for outgoing_node in self.outgoing:
                print("{}, sending {} to {}".format(self.name, data, outgoing_node))
                #send data to the node
                await outgoing_node.channel.send(data)
                print('{} sent data downstream'.format(self.name))
                await outgoing_node()
        return



    async def __call__(self, *args, **kwargs):
            print('executing {}'.format(self.name))
            if self.n_in > 0:
                data = await self.get_upstream()
            else:
                data = None
            print('{} processing data '.format(self.name))
            if len(self.data) == self.n_in:
                transformed = await self.f(self.data)
                self.data.clear()
                print("result {}".format(transformed))
                await self.send_downstream(transformed)











    @property
    def n_in(self):
        return len(self._in)

    @property
    def n_out(self):
        return len(self._out)

    @property
    def outgoing(self):
        yield from self._out

    @property
    def incoming(self):
        yield from self._in

    @property
    def has_predecessor(self):
        if self._in:
            return True
