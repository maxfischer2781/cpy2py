# - # Copyright 2016 Max Fischer
# - #
# - # Licensed under the Apache License, Version 2.0 (the "License");
# - # you may not use this file except in compliance with the License.
# - # You may obtain a copy of the License at
# - #
# - #     http://www.apache.org/licenses/LICENSE-2.0
# - #
# - # Unless required by applicable law or agreed to in writing, software
# - # distributed under the License is distributed on an "AS IS" BASIS,
# - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# - # See the License for the specific language governing permissions and
# - # limitations under the License.
"""
Compatibility for different python versions/interpeters
"""
# pylint: disable=invalid-name,undefined-variable
import sys
import logging as _logging

PY3 = sys.version_info[0] == 3

# pickle
if PY3:
    import pickle
else:
    import cPickle as pickle

# range/xrange
try:
    rangex = xrange
except NameError:
    rangex = range

# NullHandler
try:
    NullHandler = _logging.NullHandler
except AttributeError:
    class NullHandler(_logging.Handler):
        """Noop Handler, backported from py2.7"""
        def handle(self, record):
            pass

        def emit(self, record):
            pass

        def createLock(self):
            self.lock = None

__all__ = ['pickle', 'rangex', 'NullHandler']
