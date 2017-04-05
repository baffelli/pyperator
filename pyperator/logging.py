import logging as _log

class FlowLog(object):

    def __init__(self, path=None, level='AUDIT'):
        #Get log for the application
        self.log = _log.getLogger('Pype.log')
        self.log.setLevel(_log.DEBUG)
        fh = logging.