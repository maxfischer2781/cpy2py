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
import logging

from cpy2py.utility.enum import Unique
import cpy2py.ipyc


# shorthands for special kernels
TWIN_MASTER = Unique(name='Master Kernel')
TWIN_ANY_SLAVE = Unique(name='Any Twin Kernel')
TWIN_ONLY_SLAVE = Unique(name='Single Twin Kernel')

# current twin state
__kernels__ = {}  # the kernel(s) running in this interpeter
__twin_id__ = 'main'  # id of this interpreter
__is_master__ = True  # whether this is the parent process

# twin call type
__E_SHUTDOWN__ = -1

__E_CALL_FUNC__ = 1

__E_CALL_METHOD__ = 2
__E_GET_MEMBER__ = 4

__E_INSTANTIATE__ = 8
__E_REF_INCR__ = 16
__E_REF_DECR__ = 32


def is_twinterpreter(kernel_id=TWIN_ANY_SLAVE):
	"""Check whether this interpreter is running a specific kernel"""
	if kernel_id is TWIN_MASTER:
		return __is_master__
	if kernel_id is TWIN_ONLY_SLAVE:
		if len(__kernels__) != 1:
			raise RuntimeError("Twinterpeter kenrel_id '%s' is ambigious if there isn't exactly one slave." % TWIN_ONLY_SLAVE)
		return not __is_master__
	if kernel_id is TWIN_ANY_SLAVE:
		return not __is_master__
	return __twin_id__ == kernel_id


def get_kernel(kernel_id):
	assert not is_twinterpreter(kernel_id), 'Attempted call to own interpeter'
	if kernel_id is TWIN_MASTER:
		return __kernels__['main']
	if kernel_id in (TWIN_ONLY_SLAVE, TWIN_ANY_SLAVE):
		if len(__kernels__) != 1:
			raise RuntimeError("Twinterpeter kenrel_id '%s' is ambigious if there isn't exactly one slave." % TWIN_ONLY_SLAVE)
		return __kernels__.keys()[0]
	return __kernels__[kernel_id]


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
		self._instances = {}  # instance_id => instance

	def run(self):
		"""Run the kernel request server"""
		exit_code = 1
		self._logger.warning('run()')
		self._logger.warning('Starting')
		try:
			while True:
				self._logger.warning('Listening')
				request_id, directive = self.ipc.receive()
				self._logger.warning('Received: %d', request_id)
				self._logger.warning(repr(directive))
				if directive[0] == __E_CALL_FUNC__:
					self._logger.warning('Directive __E_CALL_FUNC__')
					func_obj, func_args, func_kwargs = directive[1]
					self.ipc.send((
						request_id,
						func_obj(*func_args, **func_kwargs)
					))
				elif directive[0] == __E_CALL_METHOD__:
					self._logger.warning('Directive __E_CALL_METHOD__')
					inst_id, method_name, method_args, method_kwargs = directive[1]
					self.ipc.send((
						request_id,
						getattr(self._instances[inst_id], method_name)(*method_args, **method_kwargs)
					))
				elif directive[0] == __E_GET_MEMBER__:
					self._logger.warning('Directive __E_GET_MEMBER__')
					inst_id, attribute_name = directive[1]
					self.ipc.send((
						request_id,
						getattr(self._instances[inst_id], attribute_name)
					))
				elif directive[0] == __E_INSTANTIATE__:
					self._logger.warning('Directive __E_INSTANTIATE__')
					cls, cls_args, cls_kwargs = directive[1]
					instance = cls(*cls_args, **cls_kwargs)
					self._instances[id(instance)] = instance
					self.ipc.send((
						request_id,
						id(instance)
					))
				elif directive[0] == __E_SHUTDOWN__:
					del __kernels__[self.peer_id]
					self.ipc.send((request_id, True))
					break
				else:
					raise RuntimeError
		except KeyboardInterrupt:
			pass
		except cpy2py.ipyc.IPyCTerminated:
			exit_code = 0
		except Exception:
			self._logger.warning('Shutdown:', exc_info=sys.exc_info())
		finally:
			# always free resources and exit when the kernel stops
			del self._instances
			del self.ipc
			sys.exit(exit_code)

	def _dispatch_request(self, request_type, *args):
		self._request_id += 1
		my_id = self._request_id
		self.ipc.send((my_id, (request_type, args)))
		request_id, result = self.ipc.receive()
		return result

	def dispatch_call(self, call, *call_args, **call_kwargs):
		"""
		Execute a function call and return the result
		"""
		return self._dispatch_request(__E_CALL_FUNC__, call, call_args, call_kwargs)

	def dispatch_method_call(self, instance_id, method_name, *method_args, **methods_kwargs):
		"""
		Execute a method call and return the result
		"""
		return self._dispatch_request(__E_CALL_METHOD__, instance_id, method_name, method_args, methods_kwargs)

	def get_attribute(self, instance_id, attribute_name):
		"""
		Execute a method call and return the result
		"""
		return self._dispatch_request(__E_GET_MEMBER__, instance_id, attribute_name)

	def instantiate_class(self, cls, *cls_args, **cls_kwargs):
		"""
		Instantiate a class and return its id
		"""
		return self._dispatch_request(__E_INSTANTIATE__, cls, cls_args, cls_kwargs)

	def decrement_instance_ref(self, instance_id):
		"""
		Decrement the reference count to an instance by one
		"""
		return self._dispatch_request(__E_REF_DECR__, instance_id)

	def increment_instance_ref(self, instance_id):
		"""
		Increment the reference count to an instance by one
		"""
		return self._dispatch_request(__E_REF_INCR__, instance_id)

	def stop(self):
		return self._dispatch_request(__E_SHUTDOWN__)

	def __repr__(self):
		return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())
