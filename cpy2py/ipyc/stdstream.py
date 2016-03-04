import sys
import cPickle as pickle
from cpy2py.ipyc.ipyc_exceptions import IPyCTerminated


class StdIPC(object):
	def __init__(self, readstream=sys.stdin, writestream=sys.stdout):
		self._readstream = readstream
		self._writestream = writestream

	def send(self, payload):
		pickle.dump(payload, self._writestream)
		sys.stdout.flush()

	def receive(self):
		try:
			return pickle.load(self._readstream)
		except EOFError:
			raise IPyCTerminated
