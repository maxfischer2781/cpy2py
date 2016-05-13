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
from cpy2py.kernel.kernel_exceptions import TwinterpeterUnavailable
from cpy2py.kernel import kernel_state

from cpy2py.proxy import proxy_tracker


class ProxyMethod(object):
    """
    Proxy for Methods

    :param real_method: the method object to be proxied
    """

    def __init__(self, real_method):
        self.__wrapped__ = real_method
        for attribute in ('__doc__', '__defaults__', '__name__', '__module__'):
            try:
                setattr(self, attribute, getattr(real_method, attribute))
            except AttributeError:
                pass
        assert hasattr(self, '__name__'), "%s must be able to extract method __name__" % self.__class__.__name__

    def __get__(self, instance, owner):
        if instance is None:
            subject = owner
            kernel = kernel_state.get_kernel(subject.__twin_id__)
        else:
            subject = instance
            kernel = subject.__kernel__
        return lambda *args, **kwargs: kernel.dispatch_method_call(
            subject,
            self.__name__,
            *args,
            **kwargs
        )


class TwinProxy(object):
    """
    Proxy for instances existing in another twinterpreter

    :see: Real object :py:class:`~cpy2py.proxy.proxy_object.TwinObject` for magic attributes.

    :warning: This class should never be instantiated or subclassed manually. It
              will be subclassed automatically by :py:class:`~.TwinMeta`.
    """
    __twin_id__ = None  # to be set by metaclass
    __instance_id__ = None  # to be set on __new__
    __kernel__ = None  # to be set by metaclass
    __import_mod_name__ = (None, None)  # to be set by metaclass
    __is_twin_proxy__ = True,  # recreated by metaclass

    def __new__(cls, *args, **kwargs):
        self = object.__new__(cls)
        __kernel__ = kernel_state.get_kernel(self.__twin_id__)
        object.__setattr__(self, '__kernel__', __kernel__)
        try:
            # native instance exists, but no proxy yet
            __instance_id__ = kwargs.pop('__instance_id__')
        except KeyError:
            # native instance has not been created yet
            __instance_id__ = __kernel__.instantiate_class(
                self.__class__,  # only real class can be pickled
                *args, **kwargs
            )
            object.__setattr__(self, '__instance_id__', __instance_id__)
        else:
            object.__setattr__(self, '__instance_id__', __instance_id__)
            __kernel__.increment_instance_ref(self)
        # store for later use without requiring explicit lookup/converter calls
        proxy_tracker.__active_instances__[self.__twin_id__, self.__instance_id__] = self
        return self

    def __repr__(self):
        return '<%s.%s twin proxy object at %x>' % (self.__import_mod_name__[0], self.__import_mod_name__[1], id(self))

    def __getattr__(self, name):
        return self.__kernel__.get_attribute(self, name)

    def __setattr__(self, name, value):
        return self.__kernel__.set_attribute(self, name, value)

    def __delattr__(self, name):
        return self.__kernel__.del_attribute(self, name)

    def __del__(self):
        if hasattr(self, '__instance_id__') and hasattr(self, '__twin_id__'):
            # decrement the twin reference count
            try:
                self.__kernel__.decrement_instance_ref(self)
            except (TwinterpeterUnavailable, AttributeError):
                # twin already dead, doesn't care for us anymore
                return
