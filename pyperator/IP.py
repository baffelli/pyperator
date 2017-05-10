# Based on https://github.com/LumaPictures/pflow/blob/master/pflow/packet.py



class InformationPacket(object):
    def __init__(self, value, owner=None):
        self._value = value
        self._owner = owner

    def drop(self):
        del self

    def __str__(self):
        return "Packet[owner:{}, payload type:{}]".format(self.owner, self.value.__class__.__name__)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        raise ValueError('Cannot set value, copy packet and set its value')

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, value):
        if self._owner is not None:
            raise ValueError('Packet is owned by {}, Cannot set owner, copy packet with new owner'.format(self.owner))
        else:
            self._owner = value

    @property
    def is_eos(self):
        return False


    def open(self):
        pass

    def copy(self):
        return InformationPacket(self.value, owner=None)



class EndOfStream(InformationPacket):
    """
    End of stream packet, to signal end of computation
    """
    def __init__(self):
        super(EndOfStream, self).__init__(None)

    @property
    def is_eos(self):
        return True

    def __str__(self):
        return "EOS"





class OpenBracket(InformationPacket):

    def __init__(self, owner=None):
        super(OpenBracket, self).__init__(value=None, owner=owner)

    def __str__(self):
        return "("


class CloseBracket(InformationPacket):
    def __init__(self, owner=None):
        super(CloseBracket, self).__init__(value=None, owner=owner)

    def __str__(self):
        return ")"