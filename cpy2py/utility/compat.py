"""
Compatibility for different python versions/interpeters
"""
import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

# pickle
if PY3:
    import pickle
if PY2:
    import cPickle as pickle

__all__ = ['pickle']
