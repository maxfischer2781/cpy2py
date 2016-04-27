import unittest
import time
import random

from cpy2py import TwinMaster, TwinObject, kernel_state


class StaticObject(TwinObject):
    __twin_id__ = 'pypy'

    class_attribute = 1

    @classmethod
    def cls_get(cls):
        return cls.class_attribute

    @classmethod
    def cls_set(cls, value):
        cls.class_attribute = value

    @classmethod
    def cls_scope(cls):
        return kernel_state.TWIN_ID


class TestStaticObject(unittest.TestCase):
    def setUp(self):
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.stop()
        time.sleep(0.1)

    @staticmethod
    def _get_test_args():
        return [-2500, -100, -50, -1, 0, 1, 50, 100, 2500] + \
               [int(random.random() * 200 - 100) for _ in range(5)]

    def test_scope(self):
        instance = StaticObject()
        klass = StaticObject
        self.assertEqual(instance.cls_scope(), 'pypy')
        self.assertEqual(klass.cls_scope(), 'pypy')

    def test_read(self):
        instance = StaticObject()
        klass = StaticObject
        self.assertEqual(instance.class_attribute, 1)
        self.assertEqual(instance.cls_get(), 1)
        self.assertEqual(klass.class_attribute, 1)
        self.assertEqual(klass.cls_get(), 1)

    def test_set_instance(self):
        instance = StaticObject()
        klass = StaticObject
        for arg in self._get_test_args():
            # set via instance
            instance.cls_set(arg)
            self.assertEqual(instance.class_attribute, arg)
            self.assertEqual(instance.class_attribute, klass.class_attribute)
            self.assertEqual(instance.cls_get(), arg)
            self.assertEqual(instance.cls_get(), klass.cls_get())

    def test_set_class(self):
        instance = StaticObject()
        klass = StaticObject
        for arg in self._get_test_args():
            # set via class
            klass.cls_set(arg)
            self.assertEqual(instance.class_attribute, arg)
            self.assertEqual(instance.class_attribute, klass.class_attribute)
            self.assertEqual(instance.cls_get(), arg)
            self.assertEqual(instance.cls_get(), klass.cls_get())
