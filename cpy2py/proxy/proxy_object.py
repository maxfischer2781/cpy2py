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

from cpy2py.proxy import proxy_tracker
from cpy2py.proxy.proxy_meta import TwinMeta
from cpy2py.proxy.proxy_twin import TwinProxy


def _instance_id(instance):
    """Create an instance identifier"""
    return '%X%X' % (id(instance), int(time.time() * 1000))


DOCS = """
Baseclass for objects accessible from twinterpreters

To define which twinterpeter the class is native to, set the class attribute
``__twin_id__``. It must be a :py:class:`str` identifying the native
twinterpeter.

:note: This class mainly serves to set the metaclass :py:class:`~.TwinMeta`.
       It does so in a way compatible with both python 2.X and 3.X. See the
       note on the metaclass for details.
""".strip()


def new_twin_object(cls, *args, **kwargs):  # pylint: disable=unused-argument
    """`__new__` for :py:class:`~.TwinObject` and derivatives"""
    self = object.__new__(cls)
    object.__setattr__(self, '__instance_id__', _instance_id(self))
    # register our reference for lookup
    proxy_tracker.__active_instances__[self.__twin_id__, self.__instance_id__] = self
    return self

# calling TwinMeta to set metaclass explicitly works for py2 and py3
TwinObject = TwinMeta(
    'TwinObject',
    (object,),
    {
        '__doc__': DOCS,
        #: id of interpeter where real instances exist
        '__twin_id__': None,  # to be set by metaclass or manually
        #: id of the object in the twinterpreter
        '__instance_id__': None,  # to be set on __new__
        #: tuple for twin import, of the form (<module name>, <object name>)
        '__import_mod_name__': (None, None),  # to be set by metaclass
        '__is_twin_proxy__': False,  # recreated by metaclass
        '__new__': new_twin_object,
        '__module__': __name__,
    }
)
del DOCS


def localmethod(method):
    """
    Mark method to always run in the calling twinterpreter

    :param method: method to make local
    :return: modified method

    This function can be used as a decorator in class definitions.
    """
    setattr(method, TwinMeta.mark_localmember, True)
    return method

# TwinObject and TwinProxy are not created by metaclass, initialize manually
TwinObject.__import_mod_name__ = (TwinObject.__module__, TwinObject.__name__)
TwinProxy.__import_mod_name__ = TwinObject.__import_mod_name__
