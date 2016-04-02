# - # Copyright 2016 Max Fischer
# - #
# - # Licensed under the Apache License, Version 2.0 (the "License");
# - # you may not use this file except in compliance with the License.
# - # You may obtain a copy of the License at
# - #
# - # 	http://www.apache.org/licenses/LICENSE-2.0
# - #
# - # Unless required by applicable law or agreed to in writing, software
# - # distributed under the License is distributed on an "AS IS" BASIS,
# - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# - # See the License for the specific language governing permissions and
# - # limitations under the License.
import cpy2py.twinterpreter.kernel
from cpy2py.twinterpreter.kernel_exceptions import TwinterpeterUnavailable

import proxy_tracker


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
		assert instance is not None, "%s %s must be accessed from an instance, not class" % (self.__class__.__name__, self.__name__)
		__twin_id__ = instance.__twin_id__
		__instance_id__ = instance.__instance_id__
		kernel = cpy2py.twinterpreter.kernel.get_kernel(__twin_id__)
		return lambda *args, **kwargs: kernel.dispatch_method_call(__instance_id__, self.__name__, *args, **kwargs)


class TwinProxy(object):
	"""
	Proxy for instances existing in the twinterpreter

	:warning: This class should never be instantiated or subclassed manually. It
	          will be subclassed automatically by :py:class:`~.TwinMeta`.
	"""
	__twin_id__ = None  # to be set by metaclass
	__real_class__ = None  # to be set by metaclass

	def __new__(cls, *args, **kwargs):
		self = object.__new__(cls)
		try:
			# native instance exists, but no proxy yet
			__instance_id__ = kwargs['__instance_id__']
		except KeyError:
			# native instance has not been created yet
			__instance_id__ = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__).instantiate_class(
				self.__real_class__,  # only real class can be pickled
				*args, **kwargs
			)
		else:
			cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__).increment_instance_ref(__instance_id__)
		object.__setattr__(self, '__instance_id__', __instance_id__)
		proxy_tracker.__active_instances__[self.__twin_id__, id(self)] = self
		return self

	def __repr__(self):
		return '<%s.%s twin proxy object at %x>' % (self.__class__.__module__, self.__class__.__name__, id(self))

	def __getattr__(self, name):
		kernel = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__)
		return kernel.get_attribute(self.__instance_id__, name)

	def __setattr__(self, name, value):
		kernel = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__)
		return kernel.set_attribute(self.__instance_id__, name, value)

	def __delattr__(self, name):
		kernel = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__)
		return kernel.del_attribute(self.__instance_id__, name)

	def __del__(self):
		if hasattr(self, '__instance_id__') and hasattr(self, '__twin_id__'):
			# decrement the twin reference count
			try:
				kernel = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__)
				kernel.decrement_instance_ref(self.__instance_id__)
			except TwinterpeterUnavailable:
				# __del__ during shutdown, twin already dead
				return