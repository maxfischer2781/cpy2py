import unittest
import random
import time

from cpy2py import kernel_state, TwinMaster, TwinObject, localmethod
from cpy2py.utility.compat import rangex

RND_COUNT = 500  # should be enough to avoid creating the same numbers
random_module_numbers = [random.random() for _ in rangex(RND_COUNT)]
random_global_numbers = [random.random() for _ in rangex(RND_COUNT)]


class ScopedObject(TwinObject):
    __twin_id__ = 'pypy'

    @staticmethod
    def scoped_get_module():
        return random_module_numbers

    @localmethod
    def local_get_module(self):
        return random_module_numbers

    @staticmethod
    def scoped_get_global():
        return random_global_numbers

    @localmethod
    def local_get_global(self):
        return random_global_numbers


def set_global_module_state(rgn):
    global random_global_numbers
    random_global_numbers = rgn


class TestGlobalState(unittest.TestCase):
    def setUp(self):
        kernel_state.TWIN_GROUP_STATE.add_finalizer(set_global_module_state, random_global_numbers)
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.stop()
        time.sleep(0.1)

    def test_init(self):
        instance = ScopedObject()
        self.assertEqual(instance.scoped_get_global(), instance.local_get_global())
        self.assertNotEqual(instance.scoped_get_module(), instance.local_get_module())
