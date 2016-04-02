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

from proxy_twin import TwinProxy, ProxyMethod


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
	#: proxy classes for regular classes
	__proxy_store__ = {}

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
				twin_id = cpy2py.twinterpreter.kernel.TWIN_MASTER
			class_dict['__twin_id__'] = twin_id
		# make both real and proxy class available
		real_class = mcs.__new_real_class__(name, bases, class_dict)
		proxy_class = mcs.__new_proxy_class__(name, bases, class_dict)
		# TODO: decide which gets weakref'd - MF@20160401
		# proxy_class.__real_class__ as weakref, as real_class is global anyway?
		real_class.__proxy_class__ = proxy_class
		proxy_class.__real_class__ = real_class
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
		class_dict = class_dict.copy()
		# change methods to method proxies
		for aname in class_dict.keys():
			# TODO: figure out semantics when changing __twin_id__
			# initialization should only ever happen on the real object
			if aname in ('__init__', '__new__'):
				del class_dict[aname]
			# methods must be proxy'd
			elif isinstance(class_dict[aname], types.FunctionType):
				class_dict[aname] = ProxyMethod(class_dict[aname])
			elif isinstance(class_dict[aname], (classmethod, staticmethod)):
				class_dict[aname] = ProxyMethod(class_dict[aname].__func__)
			# remove non-magic attributes so they don't shadow the real ones
			elif aname not in ('__twin_id__', '__class__', '__module__', '__doc__', '__metaclass__'):
				del class_dict[aname]
		# inherit only from proxy
		bases = (TwinProxy,)
		return type.__new__(mcs, name, bases, class_dict)

	@classmethod
	def __get_proxy_class__(mcs, baseclass):
		"""Provide a proxy twin for a class"""
		try:
			return baseclass.__proxy_class__
		except AttributeError:
			pass
		try:
			return mcs.__proxy_store__[baseclass]
		except KeyError:
			return mcs.__create_proxy_class__(baseclass)

	@classmethod
	def __create_proxy_class__(mcs, baseclass):
		"""Create a proxy twin for a regular class"""
		pass
