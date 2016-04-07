import random
import unittest
import time

from cpy2py import TwinMaster


def add(a, b):
    return a + b


def add_default(a=10, b=20):
    return a + b


class TestFunctionCall(unittest.TestCase):
    def setUp(self):
        self.twinterpreter = TwinMaster('pypy')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.stop()
        time.sleep(0.1)

    @staticmethod
    def _get_test_args():
        return [(1, 1), (50, 100), (500, 250)] + [(random.random(), random.random()) for _ in range(5)]

    def test_args(self):
        for arga, argb in self._get_test_args():
            self.assertAlmostEqual(add(arga, argb), self.twinterpreter.execute(add, arga, argb))

    def test_kwargs(self):
        for arga, argb in self._get_test_args():
            self.assertAlmostEqual(add(arga, argb), self.twinterpreter.execute(add, arga, argb))

    def test_args_defaults(self):
        for arga, argb in self._get_test_args():
            self.assertAlmostEqual(add_default(arga), self.twinterpreter.execute(add_default, arga))
            self.assertAlmostEqual(add_default(argb), self.twinterpreter.execute(add_default, argb))

    def test_kwargs_defaults(self):
        for arga, argb in self._get_test_args():
            self.assertAlmostEqual(add_default(a=arga), self.twinterpreter.execute(add_default, a=arga))
            self.assertAlmostEqual(add_default(b=argb), self.twinterpreter.execute(add_default, b=argb))
