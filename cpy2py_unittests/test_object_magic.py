import unittest

import cpy2py.twinterpreter.twin_pypy
import cpy2py.proxy.object_proxy


class MagicMethodObject(cpy2py.proxy.object_proxy.TwinObject):
	__twin_id__ = 'pypy'

	def __init__(self, numeric_value=0):
		self.numeric_value = numeric_value

	def __str__(self):
		return 'MagicMethodObject'

	# numeric comparisons
	def __lt__(self, other):
		return self.numeric_value < other

	def __gt__(self, other):
		return self.numeric_value > other


class TestObjectMagic(unittest.TestCase):
	"""Test for object magic methods"""
	def setUp(self):
		self.twinterpreter = cpy2py.twinterpreter.twin_pypy.TwinPyPy()
		self.twinterpreter.start()

	def tearDown(self):
		self.twinterpreter.stop()

	def test_numeric_comparison(self):
		instance_1 = MagicMethodObject(1)
		instance_10 = MagicMethodObject(10)
		self.assertTrue(instance_1 < 10)
		self.assertTrue(1 < instance_10)
		self.assertTrue(instance_1 < instance_10)
