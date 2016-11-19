import unittest
import time

from cpy2py import kernel_state, TwinMaster
from cpy2py.proxy import proxy_func


@proxy_func.twinfunction(kernel_state.TWIN_ID)
def native_func(arg):
    return arg


@proxy_func.twinfunction('pypy')
def proxied_func(arg):
    return arg


class TestThreadGuard(unittest.TestCase):
    def setUp(self):
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.destroy()
        time.sleep(0.1)

    def test_call_native(self):
        """Call twinfunction in native scope"""
        for arg in ('some arg', [1, 2, 3], {'a': 'A'}):
            self.assertEqual(native_func(arg), arg)

    def test_call_proxy(self):
        """Call twinfunction in other scope"""
        for arg in ('some arg', [1, 2, 3], {'a': 'A'}):
            self.assertEqual(proxied_func(arg), arg)
