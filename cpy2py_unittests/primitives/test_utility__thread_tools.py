from __future__ import print_function
import random
import unittest
import operator

from cpy2py.utility.compat import rangex
from cpy2py.utility.thread_tools import ThreadGuard


class TestThreadGuard(unittest.TestCase):
    def test_counter(self):
        counter = 1
        tg_counter = ThreadGuard(str(counter))
        for op in [
            '__add__', '__sub__', '__mul__', '__div__', '__truediv__', '__floordiv__', '__pow__', '__mod__',
            '__eq__', '__ne__', '__lt__', '__gt__', '__le__', '__ge__',
            '__and__', '__or__', '__xor__',
            '__lshift__', '__rshift__',
        ]:
            try:
                ops = getattr(operator, op)
            except AttributeError:
                continue
            else:
                for val in (random.randint(-100, 100) for _ in rangex(5)):
                    if val == 0:  # zero division
                        val = 1
                    if op in ('__lshift__', '__rshift__'):
                        val = abs(val)
                    res = ops(counter, val)
                    tg_res = ops(tg_counter, val)
                    self.assertEqual(res, tg_res, '%s %s %s %s' % (res, tg_res, op, val))
                    rres = ops(val, counter)
                    rtg_res = ops(val, tg_counter)
                    self.assertEqual(rres, rtg_res, '%s %s %s %s (reflected)' % (rres, rtg_res, op, val))
