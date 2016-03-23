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
import time

# Object setup
import cpy2py.proxy.object_proxy


def time_call(call, *args, **kwargs):
	stime = time.time()
	result = call(*args, **kwargs)
	timing = time.time() - stime
	return timing, result


def square(arg):
	return arg*arg


def compute(size):
	value = 1.5
	for _ in xrange(size):
		value *= value
		value %= 9999.9
	return value


def powerize(size):
	value = 1.1
	for _ in xrange(size):
		value *= value
	return value


def adder(size):
	value = 1.1
	for _ in xrange(size):
		value += 1.1
	return value


class TwinTest(object):
	__metaclass__ = cpy2py.proxy.object_proxy.TwinMeta
	__twin_id__ = 'pypy'

	def __init__(self):
		self.bar = 2

	def foo(self, a=2):
		"""A Foo Method"""
		return '%s says %s' % (repr(self), str(a))

	a = 2
