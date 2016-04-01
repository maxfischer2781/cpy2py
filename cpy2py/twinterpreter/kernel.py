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
"""
The kernel is the main thread of execution running inside a twinterpreter.
"""
from __future__ import print_function

import sys
import os
import time
import random
import logging

from cpy2py.utility.enum import UniqueObj
from cpy2py.utility.exceptions import format_exception
import cpy2py.ipyc
from kernel_exceptions import TwinterpeterUnavailable, TwinterpeterTerminated


# shorthands for special kernels
class TWIN_MASTER(UniqueObj):
	name = '<Master Kernel>'


class TWIN_ANY_SLAVE(UniqueObj):
	name = '<Any Twin Kernel>'


class TWIN_ONLY_SLAVE(UniqueObj):
	name = '<Single Twin Kernel>'


# current twin state
#: the kernel(s) running in this interpeter
__kernels__ = {}
#: id of this interpreter/process
__twin_id__ = 'main'
#: whether this is the parent process
__is_master__ = True
#: id of the active group of twinterpeters
__twin_group_id__ = '%08X%08X%08X' % (
	time.time() * 16,
	os.getpid(),
	random.random() * pow(16, 8)
)

# Message Enums
# twin call type
__E_SHUTDOWN__ = -1
__E_CALL_FUNC__ = 1
__E_CALL_METHOD__ = 2
__E_GET_ATTRIBUTE__ = 3
__E_SET_ATTRIBUTE__ = 4
__E_INSTANTIATE__ = 5
__E_REF_INCR__ = 6
__E_REF_DECR__ = 7
# twin reply type
__E_SUCCESS__ = 0
__E_EXCEPTION__ = 1


def is_twinterpreter(kernel_id=TWIN_ANY_SLAVE):
	"""Check whether this interpreter is running a specific kernel"""
	if kernel_id is TWIN_MASTER:
		return __is_master__
	if kernel_id is TWIN_ONLY_SLAVE:
		if len(__kernels__) != 1:
			raise RuntimeError("Twinterpeter kernel_id '%s' is ambigious if there isn't exactly one slave." % TWIN_ONLY_SLAVE)
		return not __is_master__
	if kernel_id is TWIN_ANY_SLAVE:
		return not __is_master__
	return __twin_id__ == kernel_id


def get_kernel(kernel_id):
	assert not is_twinterpreter(kernel_id), 'Attempted call to own interpeter'
	try:
		if kernel_id is TWIN_MASTER:
			return __kernels__['main']
		if kernel_id in (TWIN_ONLY_SLAVE, TWIN_ANY_SLAVE):
			if len(__kernels__) != 1:
				raise RuntimeError("Twinterpeter kernel_id '%s' is ambigious if there isn't exactly one slave." % TWIN_ONLY_SLAVE)
			return __kernels__.keys()[0]
		return __kernels__[kernel_id]
	except KeyError:
		raise TwinterpeterUnavailable(twin_id=kernel_id)


class SingleThreadKernel(object):
	"""
	Default kernel for handling requests between interpeters

	Any kernel is composed of two objects, one in each interpreter.
	"""
	def __new__(cls, peer_id, *args, **kwargs):
		assert peer_id not in __kernels__, 'Twinterpreters must have unique IDs'
		__kernels__[peer_id] = object.__new__(cls)
		return __kernels__[peer_id]

	def __init__(self, peer_id, ipc=cpy2py.ipyc.StdIPC()):
		self._logger = logging.getLogger('__cpy2py__.%s.%s' % (os.path.basename(sys.executable), peer_id))
		self.peer_id = peer_id
		self.ipc = ipc
		self._request_id = 0
		self._instances = {}  # instance_id => [ref_count, instance]

	def run(self):
		"""Run the kernel request server"""
		exit_code = 1
		self._logger.warning('run @ %s', time.asctime())
		self._logger.warning('Starting')
		try:
			while True:
				self._logger.warning('Listening')
				request_id, directive = self.ipc.receive()
				self._logger.warning('Received: %d', request_id)
				self._logger.warning(repr(directive))
				try:
					if directive[0] == __E_CALL_FUNC__:
						self._logger.warning('Directive __E_CALL_FUNC__')
						func_obj, func_args, func_kwargs = directive[1]
						response = func_obj(*func_args, **func_kwargs)
					elif directive[0] == __E_CALL_METHOD__:
						self._logger.warning('Directive __E_CALL_METHOD__')
						inst_id, method_name, method_args, method_kwargs = directive[1]
						response = getattr(self._instances[inst_id][1], method_name)(*method_args, **method_kwargs)
					elif directive[0] == __E_GET_ATTRIBUTE__:
						self._logger.warning('Directive __E_GET_MEMBER__')
						inst_id, attribute_name = directive[1]
						response = getattr(self._instances[inst_id][1], attribute_name)
					elif directive[0] == __E_SET_ATTRIBUTE__:
						self._logger.warning('Directive __E_SET_ATTRIBUTE__')
						inst_id, attribute_name, new_value = directive[1]
						response = setattr(self._instances[inst_id][1], attribute_name, new_value)
					elif directive[0] == __E_INSTANTIATE__:
						self._logger.warning('Directive __E_INSTANTIATE__')
						cls, cls_args, cls_kwargs = directive[1]
						instance = cls(*cls_args, **cls_kwargs)
						self._instances[id(instance)] = [1, instance]
						response = id(instance)
					elif directive[0] == __E_REF_DECR__:
						self._logger.warning('Directive __E_REF_DECR__')
						inst_id = directive[1][0]
						self._instances[inst_id][0] -= 1
						response = self._instances[inst_id][0]
						if self._instances[inst_id][0] <= 0:
							del self._instances[inst_id]
					elif directive[0] == __E_REF_INCR__:
						self._logger.warning('Directive __E_REF_INCR__')
						inst_id = directive[1][0]
						self._instances[inst_id][0] += 1
						response = self._instances[inst_id][0]
					elif directive[0] == __E_SHUTDOWN__:
						del __kernels__[self.peer_id]
						self.ipc.send((request_id, __E_SHUTDOWN__, True))
						break
					else:
						raise RuntimeError
				except Exception as err:
					self.ipc.send((request_id, __E_EXCEPTION__, err))
					if isinstance(err, KeyboardInterrupt):
						break
				else:
					self.ipc.send((request_id, __E_SUCCESS__, response))
		except cpy2py.ipyc.IPyCTerminated:
			exit_code = 0
		except Exception:
			self._logger.critical('TWIN KERNEL EXCEPTION')
			format_exception(self._logger, 3)
		finally:
			# always free resources and exit when the kernel stops
			del self._instances
			del self.ipc
			sys.exit(exit_code)

	# dispatching: execute actions in other interpeter
	def _dispatch_request(self, request_type, *args):
		self._request_id += 1
		my_id = self._request_id
		try:
			self.ipc.send((my_id, (request_type, args)))
			request_id, result_type, result_body = self.ipc.receive()
		except cpy2py.ipyc.IPyCTerminated:
			raise TwinterpeterTerminated(twin_id=self.peer_id)
		if result_type == __E_EXCEPTION__:
			raise result_body
		elif result_type == __E_SHUTDOWN__:
			return True
		elif result_type == __E_SUCCESS__:
			return result_body
		raise RuntimeError

	def dispatch_call(self, call, *call_args, **call_kwargs):
		"""Execute a function call and return the result"""
		return self._dispatch_request(__E_CALL_FUNC__, call, call_args, call_kwargs)

	def dispatch_method_call(self, instance_id, method_name, *method_args, **methods_kwargs):
		"""Execute a method call and return the result"""
		return self._dispatch_request(__E_CALL_METHOD__, instance_id, method_name, method_args, methods_kwargs)

	def get_attribute(self, instance_id, attribute_name):
		"""Get an attribute of an instance"""
		return self._dispatch_request(__E_GET_ATTRIBUTE__, instance_id, attribute_name)

	def set_attribute(self, instance_id, attribute_name, new_value):
		"""Set an attribute of an instance"""
		return self._dispatch_request(__E_SET_ATTRIBUTE__, instance_id, attribute_name, new_value)

	def instantiate_class(self, cls, *cls_args, **cls_kwargs):
		"""Instantiate a class, increments its reference count, and return its id"""
		return self._dispatch_request(__E_INSTANTIATE__, cls, cls_args, cls_kwargs)

	def decrement_instance_ref(self, instance_id):
		"""Decrement the reference count to an instance by one"""
		return self._dispatch_request(__E_REF_DECR__, instance_id)

	def increment_instance_ref(self, instance_id):
		"""Increment the reference count to an instance by one"""
		return self._dispatch_request(__E_REF_INCR__, instance_id)

	def stop(self):
		if self._dispatch_request(__E_SHUTDOWN__):
			del __kernels__[self.peer_id]
			return True
		return False

	def __repr__(self):
		return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())
