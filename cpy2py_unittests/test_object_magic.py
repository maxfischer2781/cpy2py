from __future__ import print_function
import unittest
import time

from cpy2py import kernel_state, TwinMaster, TwinObject


class TwinMagicObject(TwinObject):
    __twin_id__ = 'pypy'

    def __init__(self, numeric_value=0):
        self.numeric_value = numeric_value

    # numeric comparisons
    def __lt__(self, other):
        return self.numeric_value < other

    def __gt__(self, other):
        return self.numeric_value > other


class LocalMagicObject(TwinMagicObject):
    __twin_id__ = kernel_state.MASTER_ID


class TestObjectMagic(unittest.TestCase):
    """Test for object magic methods"""

    def setUp(self):
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.destroy()
        time.sleep(0.1)

    def test_remote_comparison(self):
        instance_1 = TwinMagicObject(1)
        instance_10 = TwinMagicObject(10)
        self.assertTrue(instance_1 < 10)
        self.assertTrue(1 < instance_10)
        self.assertTrue(instance_1 < instance_10)

    def test_cross_comparison(self):
        instance_1 = TwinMagicObject(1)
        instance_10 = LocalMagicObject(10)
        self.assertTrue(instance_1 < 10)
        self.assertTrue(1 < instance_10)
        self.assertTrue(instance_1 < instance_10)
