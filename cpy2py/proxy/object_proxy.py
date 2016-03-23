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
import types

import cpy2py.twinterpreter.kernel


# proxy internals
class TwinProxy(object):
	"""
	Proxy for instances existing in the twinterpreter

	:param __instance_id__: global id of this instance
	:param __twin_id__: id of the native instance's twinterpeter

	:note: Parameters must be provided via keywords.

	:warning: This class should never be instantiated or subclassed manually. It
	          will be subclassed automatically by :py:class:`~.TwinMeta`
	"""
	__twin_id__ = None  # will be set by metaclass

	def __init__(self, *args, **kwargs):
		try:
			__instance_id__ = kwargs['__instance_id__']
		except KeyError:
			# native instance has not been created yet
			__instance_id__ = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__).instantiate_class(
				type(self),
				*args, **kwargs
			)
		self.__instance_id__ = __instance_id__

	def __repr__(self):
		return '<%s.%s twin proxy object at %x>' %(self.__class__.__module__, self.__class__.__name__, id(self))


class ProxyMethod(object):
	"""
	Proxy for Methods
	"""
	def __init__(self, real_method):
		for attribute in ('__doc__', '__defaults__', '__name__', '__module__'):
			try:
				setattr(self, attribute, getattr(real_method, attribute))
			except AttributeError:
				pass
		self.__real_method__ = real_method

	def __get__(self, instance, owner):
		__twin_id__ = instance.__twin_id__
		__instance_id__ = instance.__instance_id__
		kernel = cpy2py.twinterpreter.kernel.get_kernel(__twin_id__)
		def proxy_method(*args, **kwargs):
			return kernel.dispatch_method_call(__instance_id__, self.__name__, *args, **kwargs)
		return proxy_method


class TwinMeta(type):
	"""
	Metaclass for Twin objects

	This meta-class allows using regular class definitions. In the native
	interpreter, the class is accessible directly. In any other, a proxy is
	created with all class members transformed to appropriate calls to the
	twinterpeter master.

	Using this metaclass allows setting `__twin_id__` in a class definition.
	This specifies which interpeter the class natively resides in. The default
	is always the main interpeter.
	"""
	def __new__(mcs, name, bases, class_dict):
		# find out which interpeter scope is appropriate for us
		try:
			twin_id = class_dict['__twin_id__']
		except KeyError:
			for base_class in bases:
				try:
					twin_id = base_class.__twin_id__
				except AttributeError:
					pass
				else:
					break
			else:
				twin_id = cpy2py.twinterpreter.kernel.TWIN_MASTER
			class_dict['__twin_id__'] = twin_id
		# if we are in the appropriate interpeter, proceed as normal
		if cpy2py.twinterpreter.kernel.is_twinterpreter(twin_id):
			return type.__new__(mcs, name, bases, class_dict)
		# if we are in any other interpeter, create a proxy class
		# inherit only from proxy
		bases = (TwinProxy,)
		# change methods to method proxies
		for aname in class_dict.keys():
			if aname == '__init__':
				del class_dict[aname]
			elif isinstance(class_dict[aname], types.FunctionType):
				class_dict[aname] = ProxyMethod(class_dict[aname])
		return type.__new__(mcs, name, bases, class_dict)
