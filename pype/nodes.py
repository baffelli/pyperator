from pype.utils import coroutine, message, messageList


class Node:
    def __init__(self, name, f):
        self.name = name
        self._data = None
        self._in = set()
        self._out = set()
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
        self._out.add(node)

    def add_incoming(self, node):
        self._in.add(node)

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
