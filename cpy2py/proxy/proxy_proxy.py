from cpy2py.proxy import TwinObject
from cpy2py.twinterpreter import kernel_state


class ProxyProxy(TwinObject):
    """
    Helper for proxying objects existing in the current twinterpeter

    :warning: This class is experimental at the moment.
    """
    # always stay in current twinterpeter
    __twin_id__ = kernel_state.__twin_id__

    def __init__(self, real_object):
        self._real_object = real_object

    def __getattr__(self, name):
        return getattr(self._real_object, name)

    def __setattr__(self, name, value):
        return setattr(self._real_object, name, value)

    def __delattr__(self, name):
        return delattr(self._real_object, name)
