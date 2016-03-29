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
import subprocess
import os
import errno

import kernel
import bootstrap
import cpy2py.ipyc.stdstream
from cpy2py.proxy import object_proxy


class TwinMaster(object):
	executable = None
	twinterpeter_id = None

	def __init__(self, ipc=None):
		self._process = None
		self._kernel = None
		self._ipc = ipc

	@property
	def is_alive(self):
		if self._process is not None:
			try:
				os.kill(self._process.pid, 0)
			except OSError as err:
				if err.errno == errno.EPERM:  # not allowed to kill EXISTING process
					return True
				if err.errno != errno.ESRCH:
					raise
				# no such process anymore, cleanup
				self._process = None
				self._kernel = None
			else:
				return True
		return False

	def start(self):
		self._process = subprocess.Popen(
			[
				self.executable, '-m', bootstrap.__name__,
				'--peer-id', kernel.__twin_id__,
				'--twin-id', self.twinterpeter_id,
				'--twin-group-id', kernel.__twin_group_id__,
			],
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
		)
		self._kernel = kernel.SingleThreadKernel(
			self.twinterpeter_id,
			ipc=cpy2py.ipyc.stdstream.StdIPC(
				readstream=self._process.stdout,
				writestream=self._process.stdin,
				pickler_cls=object_proxy.twin_pickler,
				unpickler_cls=object_proxy.twin_unpickler,
			)
		)

	def stop(self):
		if self._kernel is not None:
			self._kernel.stop()

	def execute(self, call, *call_args, **call_kwargs):
		assert self._kernel is not None
		return self._kernel.dispatch_call(call, *call_args, **call_kwargs)


class TwinPyPy(TwinMaster):
	"""
	PyPy twinterpreter
	"""
	executable = 'pypy'
	twinterpeter_id = 'pypy'
