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
import sys
import cPickle as pickle
from cpy2py.ipyc.ipyc_exceptions import IPyCTerminated


class StdIPC(object):
	def __init__(
			self,
			readstream=sys.stdin,
			writestream=sys.stdout,
			pickler_cls=pickle.Pickler,
			unpickler_cls=pickle.Unpickler,
			pickle_protocol=pickle.HIGHEST_PROTOCOL
	):
		self._readstream = readstream
		self._writestream = writestream
		self._pickler_cls = pickler_cls
		self._unpickler_cls = unpickler_cls
		self._pkl_protocol = pickle_protocol
		self._dump = self._pickler_cls(self._writestream, self._pkl_protocol).dump
		self._load = self._unpickler_cls(self._readstream).load

	def send(self, payload):
		try:
			self._dump(payload)
			self._writestream.flush()
		except IOError:
			raise IPyCTerminated

	def receive(self):
		try:
			return self._load()
		except EOFError:
			raise IPyCTerminated
