from __future__ import with_statement
import unittest
import time

from cpy2py import state, TwinMaster
from cpy2py.proxy import function


@function.twinfunction(state.TWIN_ID)
def native_func(arg):
    """docstring"""
    return arg


@function.twinfunction('pypy')
def proxied_func(arg):
    """docstring"""
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
        self.assertFalse(hasattr(native_func, '__wrapped__'))
        for arg in ('some arg', [1, 2, 3], {'a': 'A'}):
            self.assertEqual(native_func(arg), arg)

    def test_call_proxy(self):
        """Call twinfunction in other scope"""
        self.assertTrue(hasattr(proxied_func, '__wrapped__'))
        for arg in ('some arg', [1, 2, 3], {'a': 'A'}):
            self.assertEqual(proxied_func(arg), arg)

    def test_meta(self):
        """Twins share metadata"""
        for attr in (
            '__doc__',
            '__signature__', '__defaults__',
            '__name__', '__module__',
            '__qualname__', '__annotations__'
        ):
            with self.subTest(attr=attr):
                if hasattr(native_func, attr):
                    if attr not in ('__name__', '__qualname__'):
                        self.assertEqual(getattr(native_func, attr), getattr(proxied_func.__wrapped__, attr))
                        self.assertEqual(getattr(native_func, attr), getattr(proxied_func, attr))
                    self.assertEqual(getattr(proxied_func, attr), getattr(proxied_func.__wrapped__, attr))
