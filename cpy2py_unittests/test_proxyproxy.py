import unittest

from cpy2py import TwinMaster, TwinObject
import cpy2py.proxy.proxy_proxy  # ProxyProxy


class RealObject(object):
    class_attribute = 1

    def __init__(self):
        self.instance_attribute = 2


class PrimitiveObject(TwinObject):
    __twin_id__ = 'pypy'

    @staticmethod
    def get_proxyproxy():
        return cpy2py.proxy.proxy_proxy.ProxyProxy(RealObject())


class TestObjectPrimitives(unittest.TestCase):
    def setUp(self):
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.stop()

    def test_init(self):
        real_instance = RealObject()
        proxy_instance = PrimitiveObject.get_proxyproxy()
        self.assertIsNotNone(real_instance)
        self.assertIsNotNone(proxy_instance)
        self.assertIsInstance(real_instance, RealObject)
        self.assertNotIsInstance(proxy_instance, RealObject)
        self.assertIsInstance(proxy_instance, cpy2py.proxy.proxy_proxy.ProxyProxy)

    def test_class_attribute(self):
        real_instance = RealObject()
        proxy_instance = PrimitiveObject.get_proxyproxy()
        self.assertEqual(real_instance.class_attribute, 1)
        self.assertEqual(proxy_instance.class_attribute, 1)
        real_instance.class_attribute = 2
        proxy_instance.class_attribute += 2
        self.assertEqual(real_instance.class_attribute, 2)
        self.assertEqual(proxy_instance.class_attribute, 3)

    def test_instance_attribute(self):
        real_instance = RealObject()
        proxy_instance = PrimitiveObject.get_proxyproxy()
        self.assertEqual(real_instance.instance_attribute, 2)
        self.assertEqual(proxy_instance.instance_attribute, 2)
        real_instance.instance_attribute = 1
        proxy_instance.instance_attribute += 1
        self.assertEqual(real_instance.instance_attribute, 1)
        self.assertEqual(proxy_instance.instance_attribute, 3)
