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
import subprocess as _subprocess

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

        def createLock(self):  # nopep8
            self.lock = None

try:
    check_output = _subprocess.check_output
except AttributeError:
    def check_output(*popenargs, **kwargs):
        """Run a subprocess and return its output, backported from py2.7"""
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = _subprocess.Popen(stdout=_subprocess.PIPE, *popenargs, **kwargs)
        output, _ = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise _subprocess.CalledProcessError(retcode, cmd)
        return output

# types
try:
    stringabc = basestring
except NameError:
    stringabc = (str, bytes)

if bytes == str:
    str_to_bytes = str
else:
    def str_to_bytes(bstr):
        return bytes(bstr, 'utf-8')

try:
    unicode_str = unicode
except NameError:
    unicode_str = str

try:
    long_int = long
except NameError:
    long_int = int

try:
    intern_str = intern
except NameError:
    intern_str = sys.intern

try:
    from StringIO import StringIO as BytesFile
except ImportError:
    from io import BytesIO as BytesFile

inf = float('inf')

__all__ = [
    'pickle',
    'rangex',
    'NullHandler',
    'check_output',
    'stringabc',
    'str_to_bytes',
    'inf',
    'intern_str',
    'unicode_str',
    'long_int',
    'BytesFile',
]
