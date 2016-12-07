import sys

if sys.version_info < (3, 4):
    import unittest2
    sys.modules['unittest'] = unittest2
