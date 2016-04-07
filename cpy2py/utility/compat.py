"""
Compatibility for different python versions/interpeters
"""
# pylint: disable=invalid-name,undefined-variable
import sys

PY3 = sys.version_info[0] == 3

# pickle
if PY3:
    import pickle
else:
    import cPickle as pickle

# range/xrange
if PY3:
    rangex = range
else:
    rangex = xrange

__all__ = ['pickle', 'rangex']
