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
from __future__ import print_function
import types
from cpy2py.kernel import kernel_state

from cpy2py.proxy.proxy_twin import TwinProxy, ProxyMethod


class TwinMeta(type):
    """
    Metaclass for Twin objects

    This meta-class allows using regular class definitions. In the native
    interpreter, the class is accessible directly. In any other, a proxy is
    provided with all class members transformed to appropriate calls to the
    twinterpeter master.

    Using this metaclass allows setting ``__twin_id__`` in a class definition.
    This specifies which interpeter the class natively resides in. The default
    is always the main interpeter.

    :warning: When running code in both python 2.X and 3.X, the syntax for
              assigning metaclasses is not consistent. To circumvent this, classes
              may inherit from :py:class:`~cpy2py.proxy.proxy_object.TwinObject`,
              which sets the metaclass in a version independent way.
    """
    #: proxy classes for regular classes; real class => proxy class
    __proxy_class_store__ = {
    }
    #: real classes for proxy classes; proxy class => real class
    __real_class_store__ = {
    }
    #: attributes which are stored on the proxy as well
    __proxy_inherits_attributes__ = set((  # explicit constructor for py2.6
        '__twin_id__',  # which twinterpreter is the native one
        '__class__',  # meta-data
        '__module__',  # same
        '__doc__',  # same
        '__metaclass__',  # internal
        '__import_mod_name__',  # non-pickle loading
        '__is_twin_proxy__',  # shortcut whether object is native or not
    ))
    #: name of attribute signaling to not wrap class members
    mark_localmember = "__local_member__"

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
                twin_id = kernel_state.MASTER_ID
            class_dict['__twin_id__'] = twin_id
        # enable persistent dump/load without pickle
        class_dict['__import_mod_name__'] = (class_dict['__module__'], name)
        # consistently supply bases as real base classes
        bases = tuple(mcs.__get_real_class(base) for base in bases)
        # make both real and proxy class available
        real_class = mcs.__new_real_class__(name, bases, class_dict)
        proxy_class = mcs.__get_proxy_class__(real_class=real_class)
        mcs.register_proxy(real_class=real_class, proxy_class=proxy_class)
        # return the appropriate object or proxy for the current twin
        if kernel_state.is_twinterpreter(class_dict['__twin_id__']):
            return real_class
        else:
            return proxy_class

    # helper methods
    @classmethod
    def __new_real_class__(mcs, name, bases, class_dict):
        """Create the real twin"""
        class_dict['__is_twin_proxy__'] = False
        return type.__new__(mcs, name, bases, class_dict)

    @classmethod
    def __new_proxy_class__(mcs, name, bases, class_dict):
        """Create the proxy twin"""
        proxy_dict = class_dict.copy()
        proxy_dict['__is_twin_proxy__'] = True
        # change methods to method proxies
        for aname in class_dict:
            if getattr(proxy_dict[aname], mcs.mark_localmember, False):
                continue
            elif aname in ('__init__', '__new__'):
                del proxy_dict[aname]
            # methods must be proxy'd
            elif isinstance(proxy_dict[aname], types.FunctionType):
                proxy_dict[aname] = ProxyMethod(proxy_dict[aname])
            elif isinstance(proxy_dict[aname], (classmethod, staticmethod)):
                try:
                    real_func = proxy_dict[aname].__func__
                except AttributeError:  # py2.6
                    real_func = proxy_dict[aname].__get__(None, object)
                proxy_dict[aname] = ProxyMethod(real_func)
            # remove non-magic attributes so they don't shadow the real ones
            elif aname not in mcs.__proxy_inherits_attributes__:
                del proxy_dict[aname]
        # convert bases to proxies as well
        bases = tuple(mcs.__get_proxy_class__(base) for base in bases)
        return type.__new__(mcs, name, bases, proxy_dict)

    @classmethod
    def __get_proxy_class__(mcs, real_class):
        """Provide a proxy twin for a real class"""
        try:
            # look for already created proxy
            return mcs.__proxy_class_store__[real_class]
        except KeyError:
            # construct new proxy and register it
            proxy_class = mcs.__new_proxy_class__(real_class.__name__, real_class.__bases__, real_class.__dict__)
            mcs.register_proxy(real_class=real_class, proxy_class=proxy_class)
            return proxy_class

    @classmethod
    def __get_real_class(mcs, unknown_class):
        """Provide a real class for a proxy *or* real class"""
        try:
            return mcs.__real_class_store__[unknown_class]
        except KeyError:
            # it's a real class!
            return unknown_class

    @classmethod
    def register_proxy(mcs, real_class, proxy_class):
        """
        Register a class acting as :py:class:`~.TwinProxy` for a real class

        :param real_class: a normal, non-cpy2py class
        :type real_class: object or :py:class:`~cpy2py.proxy.proxy_object.TwinObject`
        :param proxy_class: a proxy class similar to :py:class:`~.TwinProxy`
        :type proxy_class: object or :py:class:`~.TwinProxy`
        """
        # TODO: weakref any of these? - MF@20160401
        mcs.__real_class_store__[proxy_class] = real_class
        mcs.__proxy_class_store__[real_class] = proxy_class

    # class attributes
    def __getattr__(cls, name):
        if cls.__is_twin_proxy__ and name not in TwinMeta.__proxy_inherits_attributes__:
            kernel = kernel_state.get_kernel(cls.__twin_id__)
            return kernel.get_attribute(cls, name)
        else:
            type.__getattribute__(cls, name)

    def __setattr__(cls, name, value):
        if cls.__is_twin_proxy__ and name not in TwinMeta.__proxy_inherits_attributes__:
            kernel = kernel_state.get_kernel(cls.__twin_id__)
            return kernel.set_attribute(cls, name, value)
        else:
            type.__setattr__(cls, name, value)

    def __delattr__(cls, name):
        if cls.__is_twin_proxy__ and name not in TwinMeta.__proxy_inherits_attributes__:
            kernel = kernel_state.get_kernel(cls.__twin_id__)
            return kernel.del_attribute(cls, name)
        else:
            type.__setattr__(cls, name)


TwinMeta.register_proxy(object, TwinProxy)
