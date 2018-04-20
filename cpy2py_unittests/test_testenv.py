import unittest

from cpy2py import TwinObject, state
from cpy2py.utility.compat import range
from cpy2py_unittests.utility import TestEnvironment


class VEnvObject(TwinObject):
    __twin_id__ = 'pypy_venv_test_testenv'

    class_attribute = 1

    def __init__(self, numeric_value=0):
        self.numeric_value = numeric_value

    def do_stuff(self, count):
        val = self.numeric_value
        for _ in range(int(count)):
            val *= self.numeric_value
            val %= 100
        return val

    @staticmethod
    def get_kernel_id():
        return state.TWIN_ID


class TestObjectPrimitives(unittest.TestCase):
    """Test object in virtualenv"""
    def setUp(self):
        self.test_env = TestEnvironment()
        self.test_env.add_venv_master(executable='pypy', twinterpreter_id='pypy_venv_test_testenv')
        self.test_env.start_env()

    def tearDown(self):
        self.test_env.destroy_env()

    def test_scope(self):
        """Test interpreter of object"""
        instance = VEnvObject()
        self.assertEqual(instance.get_kernel_id(), 'pypy_venv_test_testenv')
        self.assertNotEqual(instance.get_kernel_id(), state.TWIN_ID)

    def test_method_call(self):
        """Test method result"""
        instance = VEnvObject(2)
        self.assertEqual(instance.do_stuff(1E6), 52)
        instance = VEnvObject(3)
        self.assertEqual(instance.do_stuff(1E6), 3)
