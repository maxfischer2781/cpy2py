# - # Copyright 2016 Max Fischer
# - #
# - # Licensed under the Apache License, Version 2.0 (the "License");
# - # you may not use this file except in compliance with the License.
# - # You may obtain a copy of the License at
# - #
# - #     http://www.apache.org/licenses/LICENSE-2.0
# - #
# - # Unless required by applicable law or agreed to in writing, software
# - # distributed under the License is distributed on an "AS IS" BASIS,
# - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# - # See the License for the specific language governing permissions and
# - # limitations under the License.
import time
import cpy2py.twinterpreter.kernel
import cpy2py.twinterpreter.kernel_state

from cpy2py.proxy import proxy_tracker
from cpy2py.proxy.proxy_meta import TwinMeta
from cpy2py.proxy.proxy_twin import TwinProxy


def instance_id(instance):
    """Create an instance identifier"""
    return '%X%X' % (id(instance), time.time() * 1000)


class TwinObject(object):
    """
    Objects for instances accessible from twinterpreters

    To define which twinterpeter the class is native to, set the class attribute
    `__twin_id__`. It must be a :py:class:`str` identifying the native
    twinterpeter.

    :note: This class can be used in place of :py:class:`object` as a base class.
    """
    #: id of interpeter where real instances exist
    __twin_id__ = None  # to be set by metaclass or manually
    #: class of proxy for real class instances
    __proxy_class__ = TwinProxy  # to be set by metaclass
    #: id of the object in the twinterpreter
    __instance_id__ = None  # to be set on __new__
    #: tuple for twin import, of the form (<module name>, <object name>)
    __import_mod_name__ = (None, None)  # to be set by metaclass
    __metaclass__ = TwinMeta

    def __new__(cls, *args, **kwargs):
        # if we are in the appropriate interpeter, proceed as normal
        if cpy2py.twinterpreter.kernel_state.is_twinterpreter(cls.__twin_id__):
            self = object.__new__(cls)
            TwinObject.__setattr__(self, '__instance_id__', instance_id(self))
            # register our reference for lookup
            proxy_tracker.__active_instances__[self.__twin_id__, self.__instance_id__] = self
            return self
        # return a proxy to the real object otherwise
        return cls.__proxy_class__(*args, **kwargs)

# TwinObject and TwinProxy are not created by metaclass, initialize manually
TwinObject.__import_mod_name__ = (TwinObject.__module__, TwinObject.__name__)
TwinProxy.__import_mod_name__ = TwinObject.__import_mod_name__
