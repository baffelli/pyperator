from asyncio import coroutine as asco, sleep, Queue, wait

from concurrent.futures import FIRST_COMPLETED


def coroutine(func):
    def start(*args,**kwargs):
        cr = func(*args,**kwargs)
        next(cr)
        return cr
    return start


def process(fun):
    def message_expander(message_list, **kwargs):
        args={m.originator.name: m.data for m in message_list}
        kwargs.update(args)
        ret = fun(**kwargs)
        return ret
    return message_expander


def sink(fun):
    def message_expander(message_list, **kwargs):
        args={m.originator.name: m.data for m in message_list}
        kwargs.update(args)
        computed = fun(**kwargs)
        computed.send(None)
        data = (yield)
        print(data)
        computed.send(computed)
        return data
    return message_expander



# def source(func):
#     def start(*args, **kwargs):
#         gen = func(*args, **kwargs)

def push(gen):
    next(gen)




class channel(object):

    def __init__(self, name='chan', size=100, owner=None, dest=[]):
        self.name = name
        self._chan = Queue(maxsize=size)
        self.ends = {owner, *[dest]}

    def full(self):
        return len(self._chan) == self._chan.maxlen

    def connection_exists(self, source, dest):
        return {source,dest} == self.ends

    async def send(self, message):
        await self._chan.put(message)

    def receive_sync(self):
        try:
            data = self._chan.get_nowait()
        except:
            data = None
        return data

    async def receive(self):
        data = await self._chan.get()
        self._chan.task_done()
        return data

    def __repr__(self):
        return "{type}: {} <-> {}, {h}".format(*map(str,self.ends), type=type(self), h=hash(self))





class message:
    def __init__(self, content, originator):
        self.data = content
        self.originator = originator

    def __repr__(self):
        return "From: {}, data: {}".format(str(self.originator), self.data)


class messageList(set):

    def originators(self):
        return {r.originator for r in self if hasattr(r,'originator')}

    def add(self, message):
        # if message:
        super(messageList, self).add(message)

    def asdict(self):
        return {v.originator: v.data for v in self}

    def clear(self, *args, **kwargs):
        super(messageList, self).clear()

    def getfrom(self, originator):
        message_dict = self.asdict()
        return message_dict.get(originator).data

    def __repr__(self):
        # return super(messageList, self).__repr__()
    #     # return "".join([str(k) for k,v in self.items()])
        strs = ["Originator : {r}, Data: {d}".format(r=v.originator, d=v.data) for v in self]
    #     print(strs)
        return "".join(strs)