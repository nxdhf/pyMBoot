########################################################################################################################
# KBoot Exceptions
########################################################################################################################

class McuBootGenericError(Exception):
    """ Base Exception class for KBoot module """

    _fmt = 'KBoot Error'

    def __init__(self, msg=None, **kw):
        """ Initialize the Exception with given message. """
        self.msg = msg
        for key, value in kw.items():
            setattr(self, key, value)

    def __str__(self):
        """ Return the Exception message. """
        if self.msg:
            return self.msg
        try:
            return self._fmt % self.__dict__
        except (NameError, ValueError, KeyError):
            e = sys.exc_info()[1]  # current exception
            return 'Unprintable exception %s: %s' % (repr(e), str(e))

    def get_error_value(self):
        return getattr(self, 'errval', -1)


class McuBootCommandError(McuBootGenericError):
    _fmt = 'Command operation break -> %(errname)s'

    def __init__(self, msg=None, **kw):
        super().__init__(msg, **kw)

        if getattr(self, 'errname', None) is None:
            setattr(self, 'errname', 'ErrorCode = {0:d}({0:#x})'.format(self.get_error_value()))


class McuBootDataError(McuBootGenericError):
    _fmt = 'Data %(mode)s break -> %(errname)s'

    def __init__(self, msg=None, **kw):
        super().__init__(msg, **kw)

        if getattr(self, 'errname', None) is None:
            setattr(self, 'errname', 'ErrorCode = {0:d}({0:#x})'.format(self.get_error_value()))


class McuBootConnectionError(McuBootGenericError):
    _fmt = 'KBoot connection error'


class McuBootTimeOutError(McuBootGenericError):
    _fmt = 'KBoot timeout error'