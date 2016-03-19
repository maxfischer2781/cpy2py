import subprocess
import kernel
import os
import errno

import cpy2py.ipyc.stdstream


class TwinMaster(object):
	executable = None
	twinterpeter_id = None

	def __init__(self, ipc=None):
		self._process = None
		self._master = None
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
				self._master = None
			else:
				return True
		return False

	def start(self):
		self._process = subprocess.Popen(
			[
				self.executable, '-m', kernel.__name__,
				'--twin-id', self.twinterpeter_id,
				'--peer-id', kernel.__twin_id__,
			],
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
		)
		self._master = kernel.SingleThreadKernel(
			self.twinterpeter_id,
			ipc=cpy2py.ipyc.stdstream.StdIPC(
				readstream=self._process.stdout,
				writestream=self._process.stdin,
			)
		)

	def stop(self):
		if self._master is not None:
			self._master.stop()

	def execute(self, call, *call_args, **call_kwargs):
		assert self._master is not None
		return self._master.dispatch_call(call, *call_args, **call_kwargs)


class TwinPyPy(TwinMaster):
	"""
	PyPy twinterpreter
	"""
	executable = 'pypy'
	twinterpeter_id = 'pypy'
