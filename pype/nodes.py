from pype.utils import coroutine, message, messageList, asco, channel


class Node:
    def __init__(self, name, f):
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
        st = "{name} [fillcolor={c}, label=\"{name}\", style=filled]".format(c=self.color, name=self.name)
        print(st)
        return st

    def add_outgoing(self, node):
        if not node in  self._out:

            # First open channel
            current_chan = channel(name='c', source=self, dest=node)
            #Create entry
            node_entry = {node:current_chan}
            self._channels.append(current_chan)
            self._out.update(node_entry)

    def add_incoming(self, node):
        #Find channels
        open = [c.connection_exists(self, node) for c in self._channels]
        if not node in self._in:
            current_chan = channel(name='c', source=node, dest=self)
            #Create entry
            node_entry = {node:current_chan}
            self._channels.append(current_chan)
            self._in.update(node_entry)

    def remove_outgoing(self, node):
        self._out.remove(node)

    def remove_incoming(self, node):
        self._in.remove(node)



    @coroutine
    def successors(self):
        while True:
            received_data = (yield)
            for c in self.outgoing:
                c().send(received_data)


    @coroutine
    def __call__(self):
        while True:
            # Wait for ancestors to push
            received = (yield)
            self.data.add(received)
            if self.data.originators() == set(self.incoming):
                data = self.data.copy()
                self.data.clear()
            else:
                yield
            #We either have a sink or a transformation. A sink has no outputs!
            if self.n_out >0:
                transformed = self.f(data)
                message_to_send = message(transformed, self)
                self.successors().send(message_to_send)
            else:
                self.chan.send(data)

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
