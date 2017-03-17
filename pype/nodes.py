from pype.utils import messageList, channel
import asyncio

class Node:
    def __init__(self, name, f=lambda x: None):
        self.name = name
        self._data = None
        self._in = {}
        self._out = {}
        self._channels = []
        self.f = f
        self.data = messageList()
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
            # First open channel
            current_chan = channel(name='c', source=self, dest=node)
            # Create entry
            node_entry = {node: current_chan}
            self._channels.append(current_chan)
            self._out.update(node_entry)

    def add_incoming(self, node):
        # Find channels
        open = self.find_channel(node)
        if not node in self._in:
            #If the channel is not open, open it
            if not open:
                current_chan = channel(name='c', source=node, dest=self)

            else:
                current_chan = open
            # Create entry
            node_entry = {node: current_chan}
            self._in.update(node_entry)
            #Add channel
            self._channels.append(current_chan)

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
        # futures = [incoming_chan.receive() for incoming_node, incoming_chan in self.incoming]
        # if futures:
        #     completed, pending = await asyncio.wait(futures)
        #     data = [w.result() for w in completed]
        # print(data)
        # # awaitables = []
        print(list(self.incoming))
        for (incoming_node, incoming_chan) in self.incoming:
            print("{}, receiving on {}".format(self.name, incoming_chan))
            current_data = await incoming_chan.receive()
            data.append(current_data)
            print("{}, received {}".format(self.name, current_data))
        print('Done receiving')
        return data

    async def send_downstream(self, data):
        # futures = [outgoing_chan.send(data) for outgoing_node, outgoing_chan in self.outgoing]
        # if futures:
        #     completed, pending = await asyncio.wait(futures)
        #     data = [w.result() for w in completed]
        for (outgoing_node, outgoing_chan) in self.outgoing:
            print("{}, sending {} to {}".format(self.name, data, outgoing_node))
            #send data to the node
            await outgoing_chan.send(data)
            await outgoing_node()



        return 'success'



    async def __call__(self, *args, **kwargs):
        print('executing {}'.format(self.name))
        data = await self.get_upstream()
        print('{} processing data '.format(self.name))
        transformed = await self.f(data)
        sent= await self.send_downstream(transformed)
        print('{} sent data downstream {}'.format(self.name, sent))
        #Call all downstream tasks
        # futures = [outgoing() for outgoing, chan in self.outgoing]
        # if futures:
        #     completed, pending = await asyncio.wait(futures)
        # for outgoing, chan in self.outgoing:
        #     print('running {}'.format(outgoing))
        #     await outgoing()

        # return






    @property
    def n_in(self):
        return len(self._in)

    @property
    def n_out(self):
        return len(self._out)

    @property
    def outgoing(self):
        yield from self._out.items()

    @property
    def incoming(self):
        yield from self._in.items()

    @property
    def has_predecessor(self):
        if self._in:
            return True
