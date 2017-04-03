#Based on https://github.com/LumaPictures/pflow/blob/master/pflow/packet.py

import os as _os

import os.path as _path
import shutil


import tempfile

class InformationPacket(object):
    def __init__(self, value):
        self._value = value
        self._owner = None

    def drop(self):
        del self


    def __str__(self):
        return "{} owned by {}".format(str(self.value, self.owner))

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        raise ValueError('Cannot set value, copy packet and set its value')


    @property
    def owner(self):
        return self.owner

    @owner.setter
    def owner(self, value):
        if self._owner is not None:
            raise ValueError('Cannot set owner, copy packet with new owner')
        else:
            self._owner = value

    @property
    def is_eos(self):
        return False

class FilePacket(InformationPacket):

    def __init__(self, path, mode='r'):
        super(FilePacket, self).__init__(None)
        self.path = path
        self.mode = mode
        self.tempfile = tempfile.TemporaryFile()

    def open(self, mode='r'):
        return open(self.path, mode)

    def open_temp(self):
        tempfile = open(self.tempfile, 'wb+')
        return tempfile

    def finalize(self):
        shutil.copy(self.tempfile, self.path)


    @property
    def value(self):
        with self.open(self.path, self.mode) as infile:
            return infile.read()

    @property
    def exists(self):
        return _os._exists(self.path)




class EndOfStream(InformationPacket):

    @property
    def is_eos(self):
        return True
