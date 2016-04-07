"""
Compatibility for different python versions/interpeters
"""
import sys

PY3 = sys.version_info[0] == 3

# pickle
if PY3:
    import pickle
else:
    import cPickle as pickle

__all__ = ['pickle']
