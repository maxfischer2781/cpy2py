from __future__ import print_function
import unittest
import time

from cpy2py import kernel_state, TwinMaster, TwinObject


class DescriptorObject(TwinObject):
    __twin_id__ = 'pypy'

    def __init__(self, numeric_value=0):
        self.numeric_value = numeric_value

    @property
    def prop(self):
        return self.numeric_value, kernel_state.TWIN_ID

    @prop.setter
    def prop(self, value):
        self.numeric_value = value

    @prop.deleter
    def prop(self):
        self.numeric_value = 0


class TestDescriptor(unittest.TestCase):
    """Test for object magic methods"""

    def setUp(self):
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.stop()
        time.sleep(0.2)

    def test_get(self):
        instance = DescriptorObject(2)
        self.assertEqual(instance.prop, (2, 'pypy'))

    def test_set(self):
        instance = DescriptorObject(2)
        self.assertEqual(instance.prop, (2, 'pypy'))
        instance.prop = 3
        self.assertEqual(instance.prop, (3, 'pypy'))

    def test_del(self):
        instance = DescriptorObject(2)
        self.assertEqual(instance.prop, (2, 'pypy'))
        del instance.prop
        self.assertEqual(instance.prop, (0, 'pypy'))
