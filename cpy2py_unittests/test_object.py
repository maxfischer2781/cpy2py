import unittest
import time

from cpy2py import TwinMaster, TwinObject
import cpy2py.proxy.proxy_twin  # proxy type check


class PrimitiveObject(TwinObject):
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
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.destroy()
        time.sleep(0.1)

    def test_init(self):
        instance = PrimitiveObject()
        self.assertTrue(isinstance(instance, cpy2py.proxy.proxy_twin.TwinProxy))

    def test_class_attribute(self):
        instance = PrimitiveObject()
        self.assertEqual(instance.class_attribute, 1)
        instance.class_attribute = 2
        self.assertEqual(instance.class_attribute, 2)

    def test_instance_attribute(self):
        instance = PrimitiveObject()
        self.assertEqual(instance.instance_attribute, 2)
        self.assertEqual(instance.get_instance_attribute(), 2)
        instance.instance_attribute = 3
        self.assertEqual(instance.instance_attribute, 3)
        self.assertEqual(instance.get_instance_attribute(), 3)
        del instance.instance_attribute
        self.assertRaises(AttributeError, getattr, instance, 'instance_attribute')
        self.assertRaises(AttributeError, instance.get_instance_attribute)

    def test_method_call(self):
        instance = PrimitiveObject()
        self.assertEqual(instance.method(), 3)

    def test_method_args(self):
        instance = PrimitiveObject()
        self.assertEqual(instance.method_arg(), 4)
        self.assertEqual(instance.method_arg(5), 5)
        self.assertEqual(instance.method_arg(arg1=6), 6)
