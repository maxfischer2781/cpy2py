from __future__ import print_function
import random
import unittest

from cpy2py.utility.compat import range, check_output, stringabc, unicode_str, str_to_bytes
from subprocess import CalledProcessError, STDOUT


class TestCheckOutput(unittest.TestCase):
    def test_output(self):
        """Capture output from process"""
        for _ in range(20):
            val = random.random() * random.randint(0, 1000)
            self.assertEqual('%3.1f' % val, str(check_output(['python', '-c', 'print(%3.1f)' % val]).strip().decode()))

    def test_redirect(self):
        """Prevent overriding process stdout"""
        for _ in range(20):
            val = random.random() * random.randint(0, 1000)
            self.assertRaises(ValueError, check_output, ['python', '-c', 'print(%3.1f)' % val], stdout=1)

    def test_failure(self):
        """Detect failure of process"""
        self.assertRaises(CalledProcessError, check_output, ['python', '-c', 'fail<me>now'], stderr=STDOUT)


class TestStringABC(unittest.TestCase):
    def test_str(self):
        """String literal recognized as string"""
        for val in ('%X' % num for num in range(0, 5000)):
            self.assertIsInstance(val, stringabc)

    def test_unicode(self):
        """Unicode literal recognized as string"""
        for val in (u'%X' % num for num in range(0, 5000)):
            self.assertIsInstance(val, stringabc)


class TestBytes(unittest.TestCase):
    def test_str(self):
        """String literal converted to bytes"""
        for num in range(0, 5000):
            self.assertIsInstance(str_to_bytes('%X' % num), bytes)
            self.assertEqual(str_to_bytes('%X' % num), b'%X' % num)

    def test_unicode(self):
        """Unicode literal converted to bytes"""
        for num in range(0, 5000):
            self.assertIsInstance(str_to_bytes(u'%X' % num), bytes)
            self.assertEqual(str_to_bytes(u'%X' % num), b'%X' % num)


class TestUnicode(unittest.TestCase):
    def test_str(self):
        """String literal converted to unicode"""
        for num in range(0, 5000):
            self.assertIsInstance(unicode_str('%X' % num), unicode_str)
            self.assertEqual(unicode_str('%X' % num), u'%X' % num)

    def test_unicode(self):
        """Unicode literal preserved as unicode"""
        for num in range(0, 5000):
            self.assertIsInstance(unicode_str(u'%X' % num), unicode_str)
            self.assertEqual(unicode_str(u'%X' % num), u'%X' % num)
