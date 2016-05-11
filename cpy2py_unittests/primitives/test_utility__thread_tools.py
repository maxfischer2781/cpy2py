import random
import unittest
import operator

from cpy2py.utility.compat import rangex
from cpy2py.utility.thread_tools import ThreadGuard


class TestThreadGuard(unittest.TestCase):
    def test_counter(self):
        counter = 1
        tg_counter = ThreadGuard(counter)
        for op in ['add', 'sub', 'mul', 'floordiv', 'eq', 'ne', 'lt', 'gt', 'le', 'ge', 'and_', 'or_', 'xor']:
            try:
                ops = getattr(operator, op)
            except AttributeError:
                continue
            else:
                for val in (random.randint(-100, 100) for _ in rangex(5)):
                    res = ops(counter, val)
                    tg_res = ops(tg_counter, val)
                    self.assertEqual(res, tg_res, '%s %s %s' % (res, tg_res, op))
