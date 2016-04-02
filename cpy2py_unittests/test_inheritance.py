import unittest
import random

import cpy2py.twinterpreter.twin_master
import cpy2py.twinterpreter.kernel
import cpy2py.proxy.proxy_object


class PyPyBaseA1(cpy2py.proxy.proxy_object.TwinObject):
	__twin_id__ = 'pypy'

	def __init__(self, numeric_value=0):
		self.numeric_value = numeric_value

	def test_kernel(self, kernel_id=None):
		kernel_id = kernel_id if kernel_id is not None else self.__twin_id__
		return cpy2py.twinterpreter.kernel.is_twinterpreter(kernel_id=kernel_id)

	def get_instance_attribute(self):
		return self.numeric_value


class PyPyCloneA1(PyPyBaseA1):
	pass


class PyPySquareA2(PyPyCloneA1):
	def get_instance_attribute(self):
		return self.numeric_value * self.numeric_value


class PyPySquareA1(PyPyBaseA1):
	def __init__(self, numeric_value=0):
		PyPyBaseA1.__init__(self, numeric_value * numeric_value)


class PyPyDiamondA3(PyPySquareA2, PyPySquareA1):
	pass


class TestInheritance(unittest.TestCase):
	def setUp(self):
		self.twinterpreter = cpy2py.twinterpreter.twin_master.TwinPyPy()
		self.twinterpreter.start()

	def tearDown(self):
		self.twinterpreter.stop()

	@staticmethod
	def _get_test_args():
		return [-2500, -100, -50, -1, 0, 1, 50, 100, 2500] + \
			[int(random.random() * 200 - 100) for _ in xrange(5)]

	def test_direct_inheritance(self):
		for arg in self._get_test_args():
			my_instance = PyPyCloneA1(arg)
			self.assertTrue(my_instance.test_kernel(my_instance.__twin_id__))
			self.assertEqual(my_instance.numeric_value, arg)
			self.assertEqual(my_instance.get_instance_attribute(), arg)

	def test_double_inheritance(self):
		for arg in self._get_test_args():
			my_instance = PyPySquareA2(arg)
			self.assertTrue(my_instance.test_kernel(my_instance.__twin_id__))
			self.assertEqual(my_instance.numeric_value, arg)
			self.assertEqual(my_instance.get_instance_attribute(), arg * arg)

	def test_init_inheritance(self):
		for arg in self._get_test_args():
			my_instance = PyPySquareA1(arg)
			self.assertTrue(my_instance.test_kernel(my_instance.__twin_id__))
			self.assertEqual(my_instance.numeric_value, arg * arg)
			self.assertEqual(my_instance.get_instance_attribute(), arg * arg)

	def test_diamond_inheritance(self):
		for arg in self._get_test_args():
			my_instance = PyPyDiamondA3(arg)
			self.assertTrue(my_instance.test_kernel(my_instance.__twin_id__))
			self.assertEqual(my_instance.numeric_value, arg * arg)
			self.assertEqual(my_instance.get_instance_attribute(), arg * arg * arg * arg)
