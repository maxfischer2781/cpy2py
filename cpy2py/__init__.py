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
# pylint: disable=invalid-name
"""
CPy2Py
======

Multi-intepreter execution environment

`cpy2py` allows multiple interpreters to act as one application In parallel
to the main interpreter, other interpreters may be run to execute parts of
the application.

The objects available at the toplevel should be all you ever need:

* :py:class:`~cpy2py.twinterpreter.twin_master.TwinMaster` lets you slave other interpreters to do your bidding.

* :py:class:`~cpy2py.proxy.proxy_object.TwinObject` lets you create objects across interpreters.

* :py:mod:`~cpy2py.twinterpreter.kernel_state` exposes all meta information you need.
"""
import logging as _logging
import os as _os

from cpy2py.meta import __version__
from cpy2py.utility.compat import NullHandler as _NullHandler
from cpy2py.proxy.proxy_object import TwinObject, localmethod
from cpy2py.twinterpreter.twin_master import TwinMaster
from cpy2py.kernel import kernel_state


_base_logger = _logging.getLogger('__cpy2py__')
_base_logger.propagate = False
# debugging logger to stderr
if _os.environ.get('CPY2PY_DEBUG'):
    _base_logger.addHandler(_logging.StreamHandler())
    level = _os.environ.get('CPY2PY_DEBUG').upper()
    if isinstance(getattr(_logging, level, None), int):
        _base_logger.level = getattr(_logging, level)
else:
    _base_logger.addHandler(_NullHandler())

__all__ = ['TwinObject', 'TwinMaster', 'kernel_state', '__version__', 'localmethod']
