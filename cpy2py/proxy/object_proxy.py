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
import weakref
import cPickle as pickle

import cpy2py.twinterpreter.kernel
from cpy2py.twinterpreter.kernel_exceptions import TwinterpeterUnavailable

#: instances of twin objects or proxies currently alive in this twinterpeter
__active_instances__ = weakref.WeakValueDictionary()


# pickling for inter-twinterpeter communication
def persistent_twin_id(obj):
	"""Twin Pickler for inter-twinterpeter communication"""
	try:
		# twin object or proxy
		__twin_id__ = obj.__twin_id__
		if isinstance(obj, TwinMeta):
			raise AttributeError
	except AttributeError:
		# object
		return None
	else:
		try:
			# twin proxy
			return '%s\t%s\t%s' % (obj.__instance_id__, __twin_id__, pickle.dumps(type(obj)))
		except AttributeError:
			# twin object
			return '%s\t%s\t%s' % (id(obj), __twin_id__, pickle.dumps(type(obj)))


def persistent_twin_load(persid):
	"""Twin Loader for inter-twinterpeter communication"""
	instance_id, twin_id, class_pkl = persid.split('\t')
	instance_id, twin_id = int(instance_id), str(twin_id)
	try:
		return __active_instances__[twin_id, instance_id]
	except KeyError:
		# twin object always exists - persid is enough for new proxies
		return pickle.loads(class_pkl)(__twin_id__=twin_id, __instance_id__=instance_id)


def twin_pickler(*args, **kwargs):
	"""Create a Pickler capable of handling twins"""
	pickler = pickle.Pickler(*args, **kwargs)
	pickler.persistent_id = persistent_twin_id
	return pickler


def twin_unpickler(*args, **kwargs):
	"""Create an Unpickler capable of handling twins"""
	unpickler = pickle.Unpickler(*args, **kwargs)
	unpickler.persistent_load = persistent_twin_load
	return unpickler


# classes to create proxies
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
		# always forward default methods
		for aname in ['__hash__', '__cmp__']:
			if aname not in class_dict:
				class_dict[aname] = ProxyMethod(name=aname)
		return type.__new__(mcs, name, bases, class_dict)


class TwinProxy(object):
	"""
	Proxy for instances existing in the twinterpreter

	:warning: This class should never be instantiated or subclassed manually. It
	          will be subclassed automatically by :py:class:`~.TwinMeta`
	"""
	__twin_id__ = None  # will be set by metaclass

	def __new__(cls, *args, **kwargs):
		self = object.__new__(cls)
		try:
			# native instance exists, but no proxy yet
			__instance_id__ = kwargs['__instance_id__']
		except KeyError:
			# native instance has not been created yet
			__instance_id__ = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__).instantiate_class(
				type(self),
				*args, **kwargs
			)
		else:
			cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__).increment_instance_ref(__instance_id__)
		object.__setattr__(self, '__instance_id__', __instance_id__)
		__active_instances__[self.__twin_id__, id(self)] = self
		return self

	def __repr__(self):
		return '<%s.%s twin proxy object at %x>' % (self.__class__.__module__, self.__class__.__name__, id(self))

	def __getattr__(self, name):
		kernel = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__)
		return kernel.get_attribute(self.__instance_id__, name)

	def __setattr__(self, name, value):
		kernel = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__)
		return kernel.set_attribute(self.__instance_id__, name, value)

	def __del__(self):
		if hasattr(self, '__instance_id__') and hasattr(self, '__twin_id__'):
			try:
				kernel = cpy2py.twinterpreter.kernel.get_kernel(self.__twin_id__)
			except TwinterpeterUnavailable:
				# __del__ during shutdown, twin already dead
				pass
			else:
				kernel.decrement_instance_ref(self.__instance_id__)

	def __setstate__(self, state):
		object.__setattr__(self, '__instance_id__', state['__instance_id__'])


class ProxyMethod(object):
	"""
	Proxy for Methods

	:param real_method: the function/method object to be proxied
	:param name: name of the function/method to be proxied

	:note: It is in general sufficient to supply either `real_method` *or*
	       `name`.
	"""
	def __init__(self, real_method=None, name=None):
		if real_method is not None:
			for attribute in ('__doc__', '__defaults__', '__name__', '__module__'):
				try:
					setattr(self, attribute, getattr(real_method, attribute))
				except AttributeError:
					pass
		if name is not None:
			self.__name__ = name
		assert hasattr(self, '__name__')

	def __get__(self, instance, owner):
		__twin_id__ = instance.__twin_id__
		__instance_id__ = instance.__instance_id__
		kernel = cpy2py.twinterpreter.kernel.get_kernel(__twin_id__)
		return lambda *args, **kwargs: kernel.dispatch_method_call(__instance_id__, self.__name__, *args, **kwargs)


class TwinObject(object):
	"""
	Objects for instances accessible from twinterpreters

	To define which twinterpeter the class is native to, set the class attribute
	`__twin_id__`. It must be a :py:class:`str` identifying the native
	twinterpeter.

	:note: This class can be used in place of :py:class:`object` as a base class.
	"""
	__twin_id__ = cpy2py.twinterpreter.kernel.TWIN_MASTER
	__metaclass__ = TwinMeta

	def __new__(cls, *args, **kwargs):
		self = object.__new__(cls)
		__active_instances__[self.__twin_id__, id(self)] = self
		return self
