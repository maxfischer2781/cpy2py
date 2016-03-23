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
import argparse
import os

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
__E_CALL_CTOR__ = 8


def is_twinterpreter(kernel_id=TWIN_ANY_SLAVE):
	"""Check whether this interpreter is running a specific kernel"""
	if kernel_id is TWIN_MASTER:
		return __is_master__
	if kernel_id is TWIN_ONLY_SLAVE:
		if len(__kernels__) != 1:
			raise RuntimeError("Twinterpeter kenerl_id '%s' is ambigious if there isn't exactly one slave." % TWIN_ONLY_SLAVE)
		return not __is_master__
	if kernel_id is TWIN_ANY_SLAVE:
		return not __is_master__
	return __twin_id__ == kernel_id


def get_kernel(kernel_id):
	assert not is_twinterpreter, 'Attempted call to own interpeter'
	if kernel_id is TWIN_MASTER:
		return __kernels__['main']
	if kernel_id in (TWIN_ONLY_SLAVE, TWIN_ANY_SLAVE):
		if len(__kernels__) != 1:
			raise RuntimeError("Twinterpeter kenerl_id '%s' is ambigious if there isn't exactly one slave." % TWIN_ONLY_SLAVE)
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
		self.peer_id = peer_id
		self.ipc = ipc
		self._request_id = 0
		self._instances = {}  # instance_id => instance

	def run(self):
		"""Run the kernel request server"""
		try:
			while True:
				request_id, directive = self.ipc.receive()
				if directive[0] == __E_CALL_FUNC__:
					self.ipc.send((
						request_id,
						directive[1](*directive[2], **directive[3])
					))
				elif directive[0] == __E_CALL_METHOD__:
					pass
				elif directive[0] == __E_SHUTDOWN__:
					del __kernels__[self.peer_id]
					self.ipc.send((request_id, True))
					break
				else:
					raise RuntimeError
		except KeyboardInterrupt:
			pass
		except cpy2py.ipyc.IPyCTerminated:
			pass

	def dispatch_call(self, call, *call_args, **call_kwargs):
		self._request_id += 1
		my_id = self._request_id
		self.ipc.send((my_id, (__E_CALL_FUNC__, call, call_args, call_kwargs)))
		request_id, result = self.ipc.receive()
		return result

	def dispatch_method_call(self, instance_id, method_name, *method_args, **methods_kwargs):
		pass

	def stop(self):
		self._request_id += 1
		my_id = self._request_id
		self.ipc.send((my_id, (__E_SHUTDOWN__, )))
		request_id, result = self.ipc.receive()
		del __kernels__[self.peer_id]
		return result

	def __repr__(self):
		return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())
