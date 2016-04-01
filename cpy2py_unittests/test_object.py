import unittest

import cpy2py.twinterpreter.twin_master
import cpy2py.proxy.object_proxy


class PrimitiveObject(cpy2py.proxy.object_proxy.TwinObject):
	__twin_id__ = 'pypy'

	class_attribute = 1

	def __init__(self):
		self.instance_attribute = 2

	@staticmethod
	def method():
		return 3

	@staticmethod
	def method_arg(arg1=4):
		return arg1

	def get_instance_attribute(self):
		return self.instance_attribute


class TestObjectPrimitives(unittest.TestCase):
	def setUp(self):
		self.twinterpreter = cpy2py.twinterpreter.twin_master.TwinPyPy()
		self.twinterpreter.start()

	def tearDown(self):
		self.twinterpreter.stop()

	def test_init(self):
		instance = PrimitiveObject()
		self.assertIsInstance(instance, cpy2py.proxy.object_proxy.TwinProxy)

	def test_class_attribute(self):
		self.assertEqual(PrimitiveObject().class_attribute, 1)

	def test_instance_attribute(self):
		instance = PrimitiveObject()
		self.assertEqual(instance.instance_attribute, 2)
		self.assertEqual(instance.get_instance_attribute(), 2)
		instance.instance_attribute = 3
		self.assertEqual(instance.instance_attribute, 3)
		self.assertEqual(instance.get_instance_attribute(), 3)

	def test_method_call(self):
		instance = PrimitiveObject()
		self.assertEqual(instance.method(), 3)

	def test_method_args(self):
		instance = PrimitiveObject()
		self.assertEqual(instance.method_arg(), 4)
		self.assertEqual(instance.method_arg(5), 5)
		self.assertEqual(instance.method_arg(arg1=6), 6)
