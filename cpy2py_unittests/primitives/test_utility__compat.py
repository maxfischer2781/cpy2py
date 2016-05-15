from __future__ import print_function
import random
import unittest

from cpy2py.utility.compat import rangex, check_output
from subprocess import CalledProcessError, STDOUT


class TestCheckOutput(unittest.TestCase):
    def test_output(self):
        for _ in rangex(20):
            val = random.random() * random.randint(0, 1000)
            self.assertEqual('%3.1f' % val, check_output(['python', '-c', 'print(%3.1f)' % val]).strip())

    def test_redirect(self):
        for _ in rangex(20):
            val = random.random() * random.randint(0, 1000)
            self.assertRaises(ValueError, check_output, ['python', '-c', 'print(%3.1f)' % val], stdout=1)

    def test_failure(self):
        self.assertRaises(CalledProcessError, check_output, ['python', '-c', 'fail<me>now'], stderr=STDOUT)
