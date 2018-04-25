import unittest
import os

from cpy2py.utility import twinspect
import cpy2py_unittests


class TestExecutablePath(unittest.TestCase):
    def test_path_missing(self):
        """path does not exist"""
        with self.assertRaises(OSError):
            twinspect.exepath('/no/such/path/exists')

    def test_path_executable(self):
        """path is executable"""
        exe_path = os.path.join(os.path.dirname(cpy2py_unittests.__file__), 'data', 'executable.py')
        self.assertEqual(
            twinspect.exepath(exe_path),
            exe_path
        )

    def test_path_nonexecutable(self):
        """path is not executable"""
        exe_path = os.path.join(os.path.dirname(cpy2py_unittests.__file__), 'data', 'dummy.txt')
        with self.assertRaises(OSError):
            twinspect.exepath(exe_path)

    def test_sys_path(self):
        """search executable in PATH"""
        exe_path = os.path.join(os.path.dirname(cpy2py_unittests.__file__), 'data', 'executable.py')
        old_path = os.environ.get('PATH')
        # single path item
        os.environ['PATH'] = os.path.dirname(exe_path)
        self.assertEqual(twinspect.exepath('executable.py'), exe_path)
        # last path item
        os.environ['PATH'] = '/no/such/path/exists' + os.pathsep + os.path.dirname(exe_path)
        self.assertEqual(twinspect.exepath('executable.py'), exe_path)
        # first path item
        os.environ['PATH'] = os.path.dirname(exe_path) + os.pathsep + '/no/such/path/exists'
        self.assertEqual(twinspect.exepath('executable.py'), exe_path)
        # wrong items in path
        os.environ['PATH'] = '/no/such/path/exists/here' + os.pathsep + '/no/such/path/exists/either'
        with self.assertRaises(OSError):
            twinspect.exepath('executable.py')
        # no items in path
        os.environ['PATH'] = ''
        with self.assertRaises(OSError):
            twinspect.exepath('executable.py')
        # reset
        if old_path is None:
            del os.environ['PATH']
        else:
            os.environ['PATH'] = old_path
