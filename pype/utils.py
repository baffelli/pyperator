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

    def __getitem__(self, item):
        super(messageList,self).remove()

    def __repr__(self):
        # return super(messageList, self).__repr__()
    #     # return "".join([str(k) for k,v in self.items()])
        strs = ["Originator : {r}, Data: {d}".format(r=v.originator, d=v.data) for v in self]
    #     print(strs)
        return "".join(strs)