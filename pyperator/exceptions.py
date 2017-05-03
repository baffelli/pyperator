class ComponentError(BaseException):
    def __init__(self, message, component, *args):
        try:
            new_message = "Component {}: {}".format(component, message)
        except:
            new_message = 'fail'
        super(ComponentError, self).__init__(new_message)


class PortError(Exception):
    def __init__(self, message, channel, *args):
        new_message = "Component {component}: Port {name} {message}".format(component=channel.component, name=channel.name, message=message)
        super(PortError, self).__init__(new_message)


class PortNotExistingError(ComponentError):
    def __init__(self, component, item, *args):
        ComponentError.__init__(self, "port {} does not exist.".format(item), component, *args)


class StopComputation(StopIteration):
    pass


class PortAlreadyConnectedError(PortError):
    def __init__(self, channel, other_channel, *args):
        super(PortAlreadyConnectedError, self).__init__("is already connected to {}".format(other_channel), channel)


class PortAlreadyExistingError(PortError):
    def __init__(self, channel, other_channel, *args):
        super(PortAlreadyExistingError, self).__init__("already exists".format(other_channel), channel)

class PortDisconnectedError(PortError):
    def __init__(self, channel, *args):
        super(PortDisconnectedError, self).__init__("is disconnected", channel)


class OutputOnlyError(PortError):
    def __init__(self, channel, *args):
        super(OutputOnlyError, self).__init__("is a OutputPort, it cannot be used to receive.", channel, *args)


class InputOnlyError(PortError):
    def __init__(self, channel, *args):
        super(InputOnlyError, self).__init__("is a InputPort, it cannot be used to send.", channel, *args)


class MultipleConnectionError(PortError):
    def __init__(self, channel, *args):
        super(MultipleConnectionError, self).__init__("an InputPort only supports one incoming connection.", channel, *args)


class PortClosedError(PortError):
    def __init__(self, channel, *args):
        super(PortClosedError, self).__init__("is closed", channel, *args)


class FormatterError(Exception):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class WildcardNotExistingError(Exception):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class CommandFailedError(ComponentError):
    def __init__(self,component, message, *args):
        ComponentError.__init__(self, message, component)


class FileExistingError(Exception):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class FileNotExistingError(Exception):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class PacketOwnedError(Exception):
    def __init__(self, *args, **kwargs):
        BaseException.__init__(self, *args, **kwargs)


class NotCoroutineError(Exception):
    def __init__(self, fun, *args, **kwargs):
        base_message = "Function {name} is not a coroutine".format(name=fun.__name__)
        BaseException.__init__(self,base_message, *args, **kwargs)
