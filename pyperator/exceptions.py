class ComponentException(BaseException):
    def __init__(self, message, component, *args):
        try:
            new_message = "Component {}: {}".format(component, message)
        except:
            new_message = 'fail'
        super(ComponentException,self).__init__(new_message, *args)


class PortException(BaseException):
    def __init__(self, message, channel, *args):
        try:
            new_message = "Component {}: Port {} {}".format(channel.component, channel.name, message)
        except:
            new_message = 'fail'
        super(PortException,self).__init__(new_message, *args)


class PortNotExistingException(ComponentException):
    def __init__(self, component, item, *args):
        super(PortNotExistingException, self).__init__("port {} does not exist.".format(item), component)


class StopComputation(StopIteration):
    pass


class PortDisconnectedError(PortException):
    def __init__(self, channel, *args):
        super(PortDisconnectedError, self).__init__("is disconnected", channel)


class OutputOnlyError(PortException):
    def __init__(self, channel, *args):
        super(OutputOnlyError, self).__init__("is a OutputPort, it cannot be used to receive.", channel, *args)


class InputOnlyError(PortException):
    def __init__(self, channel, *args):
        super(InputOnlyError, self).__init__("is a InputPort, it cannot be used to send.", channel, *args)


class MultipleConnectionError(BaseException):
    pass


class PortClosedError(PortException):
    def __init__(self, channel, *args):
        super(PortClosedError, self).__init__("is closed", channel, *args)


class FormatterError(BaseException):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class WildcardNotExistingError(BaseException):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class CommandFailedError(ComponentException):
    def __init__(self,component, message, *args):
        ComponentException.__init__(self, message, component)


class FileExistingError(BaseException):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class FileNotExistingError(BaseException):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class PacketOwnedError(BaseException):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)