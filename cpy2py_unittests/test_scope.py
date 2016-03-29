import unittest

import cpy2py.twinterpreter.twin_pypy
import cpy2py.twinterpreter.kernel
import cpy2py.proxy.object_proxy


def test_kernel(kernel_id):
	return cpy2py.twinterpreter.kernel.is_twinterpreter(kernel_id=kernel_id)


class PyPyObject(cpy2py.proxy.object_proxy.TwinObject):
	__twin_id__ = 'pypy'

	def test_kernel(self, kernel_id=None):
		kernel_id = kernel_id if kernel_id is not None else self.__twin_id__
		return cpy2py.twinterpreter.kernel.is_twinterpreter(kernel_id=kernel_id)


class TestCallScope(unittest.TestCase):
	def setUp(self):
		self.twinterpreter = cpy2py.twinterpreter.twin_pypy.TwinPyPy()
		self.twinterpreter.start()

	def tearDown(self):
		self.twinterpreter.stop()

	def test_method(self):
		pypy_instance = PyPyObject()
		self.assertTrue(pypy_instance.test_kernel())
		self.assertTrue(pypy_instance.test_kernel('pypy'))
		self.assertFalse(pypy_instance.test_kernel('foobar'))

	def test_function(self):
		self.assertTrue(test_kernel(cpy2py.twinterpreter.kernel.__twin_id__))
		self.assertTrue(test_kernel(cpy2py.twinterpreter.kernel.TWIN_MASTER))
		self.assertFalse(test_kernel(cpy2py.twinterpreter.kernel.TWIN_ONLY_SLAVE))
		self.assertFalse(test_kernel('foobar'))
		self.assertTrue(self.twinterpreter.execute(test_kernel, self.twinterpreter.twinterpeter_id))
		self.assertTrue(self.twinterpreter.execute(test_kernel, 'pypy'))
		self.assertTrue(self.twinterpreter.execute(test_kernel, cpy2py.twinterpreter.kernel.TWIN_ONLY_SLAVE))
		self.assertFalse(self.twinterpreter.execute(test_kernel, 'foobar'))
