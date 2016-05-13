import unittest
import time

from cpy2py import kernel_state, TwinMaster, TwinObject
from cpy2py.proxy.proxy_object import localmethod


def test_kernel(kernel_id):
    return kernel_state.is_twinterpreter(kernel_id=kernel_id)


class PyPyObject(TwinObject):
    __twin_id__ = 'pypy'

    def test_kernel(self, kernel_id=None):
        kernel_id = kernel_id if kernel_id is not None else self.__twin_id__
        return kernel_state.is_twinterpreter(kernel_id=kernel_id)

    @localmethod
    def local_kernel(self):
        return kernel_state.TWIN_ID

    def deferred_local_kernel(self):
        return self.local_kernel()


class TestCallScope(unittest.TestCase):
    def setUp(self):
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.stop()
        time.sleep(0.1)

    def test_method(self):
        pypy_instance = PyPyObject()
        self.assertTrue(pypy_instance.test_kernel())
        self.assertTrue(pypy_instance.test_kernel('pypy'))
        self.assertFalse(pypy_instance.test_kernel('foobar'))

    def test_function_native(self):
        self.assertTrue(test_kernel(kernel_state.TWIN_ID))
        self.assertTrue(test_kernel(kernel_state.MASTER_ID))
        self.assertFalse(test_kernel('pypy'))
        self.assertFalse(test_kernel('foobar'))

    def test_function_twin(self):
        self.assertTrue(self.twinterpreter.execute(test_kernel, self.twinterpreter.twinterpreter_id))
        self.assertTrue(self.twinterpreter.execute(test_kernel, 'pypy'))
        self.assertFalse(self.twinterpreter.execute(test_kernel, 'foobar'))

    def test_local_method(self):
        pypy_instance = PyPyObject()
        # call from master scope
        self.assertEqual(pypy_instance.local_kernel(), kernel_state.MASTER_ID)
        # bounce via regular method
        self.assertEqual(pypy_instance.deferred_local_kernel(), 'pypy')
