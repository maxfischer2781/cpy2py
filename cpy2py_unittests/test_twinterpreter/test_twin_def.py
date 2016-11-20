import unittest
import sys
import os

from cpy2py.twinterpreter import twin_def


class TestTwinDef(unittest.TestCase):
    def test_init_executable(self):
        """Initialize with executable only"""
        # from full path
        instance_a = twin_def.TwinDef(executable=sys.executable)
        self.assertEqual(sys.executable, instance_a.executable)
        self.assertEqual(os.path.basename(sys.executable), instance_a.twinterpreter_id)
        os_path = os.environ.get('PATH')
        os.environ['PATH'] = os.path.dirname(sys.executable)
        instance_b = twin_def.TwinDef(executable=os.path.basename(sys.executable))
        self.assertEqual(sys.executable, instance_b.executable)
        self.assertEqual(os.path.basename(sys.executable), instance_b.twinterpreter_id)
        os.environ['PATH'] = os_path
        self.assertEqual(instance_a, instance_b)

    def test_init_twinid(self):
        """Initialize with twinterpreter id only"""
        os_path = os.environ.get('PATH')
        os.environ['PATH'] = os.path.dirname(sys.executable)
        instance_b = twin_def.TwinDef(twinterpreter_id=os.path.basename(sys.executable))
        self.assertEqual(sys.executable, instance_b.executable)
        self.assertEqual(os.path.basename(sys.executable), instance_b.twinterpreter_id)
        os.environ['PATH'] = os_path
