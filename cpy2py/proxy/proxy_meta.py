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
import types
import cpy2py.twinterpreter.kernel
import cpy2py.twinterpreter.kernel_state

from cpy2py.proxy.proxy_twin import TwinProxy, ProxyMethod


class TwinMeta(type):
    """
    Metaclass for Twin objects

    This meta-class allows using regular class definitions. In the native
    interpreter, the class is accessible directly. In any other, a proxy is
    provided with all class members transformed to appropriate calls to the
    twinterpeter master.

    Using this metaclass allows setting `__twin_id__` in a class definition.
    This specifies which interpeter the class natively resides in. The default
    is always the main interpeter.

    :warning: This metaclass should never be assigned manually. Classes should
              inherit from :py:class:`~.TwinObject`, which sets the metaclass
              automaticaly. You only ever need to set the metaclass if you
              derive a new metaclass from this one.
    """
    #: proxy classes for regular classes; real class => proxy class
    __proxy_store__ = {
        object: TwinProxy
    }
    #: attributes which are stored on the proxy as well
    __proxy_inherits_attributes__ = [
        '__twin_id__',
        '__class__',
        '__module__',
        '__doc__',
        '__metaclass__',
        '__import_mod_name__'
    ]

    def __new__(mcs, name, bases, class_dict):
        """Create twin object and proxy"""
        # find out which interpeter scope is appropriate for us
        if class_dict.get('__twin_id__') is None:
            for base_class in bases:
                try:
                    twin_id = base_class.__twin_id__
                except AttributeError:
                    pass
                else:
                    break
            else:
                twin_id = cpy2py.twinterpreter.kernel_state.MASTER_ID
            class_dict['__twin_id__'] = twin_id
        # enable persistent dump/load without pickle
        class_dict['__import_mod_name__'] = (class_dict['__module__'], name)
        # make both real and proxy class available
        real_class = mcs.__new_real_class__(name, bases, class_dict)
        proxy_class = mcs.__get_proxy_class__(real_class=real_class)
        mcs.__register_classes__(real_class=real_class, proxy_class=proxy_class)
        # always return real_class, let its __new__ sort out the rest
        return real_class

    # helper methods
    @classmethod
    def __new_real_class__(mcs, name, bases, class_dict):
        """Create the real twin"""
        return type.__new__(mcs, name, bases, class_dict)

    @classmethod
    def __new_proxy_class__(mcs, name, bases, class_dict):
        """Create the proxy twin"""
        proxy_dict = class_dict.copy()
        # change methods to method proxies
        for aname in class_dict:
            if aname in ('__init__', '__new__'):
                del proxy_dict[aname]
            # methods must be proxy'd
            elif isinstance(proxy_dict[aname], types.FunctionType):
                proxy_dict[aname] = ProxyMethod(proxy_dict[aname])
            elif isinstance(proxy_dict[aname], (classmethod, staticmethod)):
                try:
                    real_func = proxy_dict[aname].__func__
                except AttributeError:  # py2.6
                    real_func = proxy_dict[aname].__get__(object)
                proxy_dict[aname] = ProxyMethod(real_func)
            # remove non-magic attributes so they don't shadow the real ones
            elif aname not in mcs.__proxy_inherits_attributes__:
                del proxy_dict[aname]
        # convert bases to proxies as well
        bases = tuple(mcs.__get_proxy_class__(base) for base in bases)
        return type.__new__(mcs, name, bases, proxy_dict)

    @classmethod
    def __get_proxy_class__(mcs, real_class):
        """Provide a proxy twin for a class"""
        try:
            # look for already created proxy
            return getattr(real_class, "__proxy_class__", mcs.__proxy_store__[real_class])
        except KeyError:
            # construct new proxy and register it
            proxy_class = mcs.__new_proxy_class__(real_class.__name__, real_class.__bases__, real_class.__dict__)
            mcs.__register_classes__(real_class=real_class, proxy_class=proxy_class)
            return proxy_class

    @classmethod
    def __register_classes__(mcs, real_class, proxy_class):
        # TODO: decide which gets weakref'd - MF@20160401
        # proxy_class.__real_class__ as weakref, as real_class is global anyway?
        proxy_class.__real_class__ = real_class
        try:
            real_class.__proxy_class__ = proxy_class
        except TypeError:
            # builtins
            mcs.__proxy_store__[real_class] = proxy_class
