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


class TwinProxy(object):
	"""
	Proxy for instances existing in the twinterpreter
	"""
	def __init__(self, instance_id, twin_id, members, methods):
		self.__twin_id__ = twin_id
		self.__instance_id__ = instance_id
		self.__twin_members__ = members
		self.__twin_methods__ = methods

	# value member access
	def __getattr__(self, item):
		if item in self.__twin_members__:
			return


class TwinMeta(type):
	"""
	Metaclass for Twin objects

	This meta-class allows using regular class definitions. In the native
	interpreter, the class is accessible directly. In any other, a proxy is
	created with all class members transformed to appropriate calls to the
	twinterpeter master.
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

