import unittest
import time

from cpy2py import kernel_state, TwinMaster, TwinObject
from cpy2py.utility.compat import rangex


class PyPyng(TwinObject):
    __twin_id__ = 'pypy'

    def play(self, opponent, recursion=0):
        if recursion <= 0:
            return self.__class__.__name__
        return opponent.play(self, recursion-1)


class Pyng(PyPyng):
    __twin_id__ = kernel_state.MASTER_ID


class TestPingPongCall(unittest.TestCase):
    def setUp(self):
        self.twinterpreter = TwinMaster(twinterpreter_id='pypy', kernel='async')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.stop()
        time.sleep(0.1)

    def test_bounce_none(self):
        pypy_instance = PyPyng()
        py_instance = Pyng()
        self.assertEqual(pypy_instance.__class__.__name__, pypy_instance.play(py_instance, 0))
        self.assertEqual(py_instance.__class__.__name__, py_instance.play(pypy_instance, 0))

    def test_bounce_one(self):
        pypy_instance = PyPyng()
        py_instance = Pyng()
        self.assertEqual(py_instance.__class__.__name__, pypy_instance.play(py_instance, 1))
        self.assertEqual(pypy_instance.__class__.__name__, py_instance.play(pypy_instance, 1))

    def test_bounce_any(self):
        pypy_instance = PyPyng()
        py_instance = Pyng()
        for bounces in rangex(1, 20, 2):
            self.assertEqual(py_instance.__class__.__name__, pypy_instance.play(py_instance, bounces))
            self.assertEqual(pypy_instance.__class__.__name__, py_instance.play(pypy_instance, bounces))
        for bounces in rangex(0, 20, 2):
            self.assertEqual(pypy_instance.__class__.__name__, pypy_instance.play(py_instance, bounces))
            self.assertEqual(py_instance.__class__.__name__, py_instance.play(pypy_instance, bounces))

    def test_bounce_lots(self):
        pypy_instance = PyPyng()
        py_instance = Pyng()
        for bounces in rangex(1, 200, 20):
            self.assertEqual(py_instance.__class__.__name__, pypy_instance.play(py_instance, bounces))
            self.assertEqual(pypy_instance.__class__.__name__, py_instance.play(pypy_instance, bounces))
        for bounces in rangex(0, 200, 20):
            self.assertEqual(pypy_instance.__class__.__name__, pypy_instance.play(py_instance, bounces))
            self.assertEqual(py_instance.__class__.__name__, py_instance.play(pypy_instance, bounces))
