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
to the main interpreter, other interpreters may run to execute parts of the
application.

*cpy2py let's CPython and PyPy see eye to eye.*

Quick Guide
===========

Twinterpreters and TwinMasters
------------------------------

A twinterpreter is simply another interpreter running as a subprocess -
with some glue and magic sprinkled on it. You can control and create them
using a :py:class:`TwinMaster`.

You should only ever worry about two methods: :py:meth:`~TwinMaster.start`
launches the twinterpreter. :py:meth:`~TwinMaster.execute` executes
an arbitrary callable in the twinterpreter.

.. code:: python

    from my_module import my_function
    twinterpreter = TwinMaster('pypy')
    twinterpreter.start()
    twinterpreter.execute(my_function, 1, 2, 3, 'ka-pow!', doctor="who?")

TwinObjects
-----------

The real power of :py:mod:`cpy2py` are Twins - objects living in one
twinterpreter and being represented by proxies in any other interpeter.
Using twins, you can seamlessly split your application across multiple
twins.

You create twins by inheriting from :py:class:`~.TwinObject` instead of
:py:class:`object` and setting a `__twin_id__`. That's it.

.. code:: python

    from cpy2py import TwinObject
    class SuperComputer(TwinObject):
        __twin_id__ = 'pypy'  # makes class native to pypy twinterpeter

        def megaloop(self, x, y):
            return sum(a+b for a in range(x) for b in range(y))

    class CWrapper(TwinObject):
        __twin_id__ = 'python'  # makes class native to python twinterpeter

        def callme(self, who, what="buy milk"):
            return some_clib.c_fcn_cll_cplx_xmpl(who, what)

If you don't set `__twin_id__` on a child of :py:class:`~.TwinObject`,
the class will always be native to the main interpreter. Handy for all
the stuff that's needed everywhere but really doesn't belong anywhere.

:note: At the moment, you have to explicitly start a class's native
       twinterpreter before instantiating the class. Only the main
       interpreter is always available, of course.

Debugging
---------

The core of :py:mod:`cpy2py` supports some :py:mod:`logging` facilities.
All such loggers are children of the `__cpy2py__` logger. By default,
no active handlers are attached and propagation is disabled. If needed,
you reconfigure them like any other :py:mod:`logging` logger to suit your
needs.

For small scale debugging, one can set the environment variable
:envvar:`CPY2PY_DEBUG`. If it is defined and not empty, logging output
is written to `stderr`.

Note that loggers are meant for development and only address the internal
state. Your application should not depend on this information. Unless
:py:mod:`cpy2py` misbehaves (or you suspect it to), ignore its logging.

.. end_long_description

Instant awesome, just add water
===============================

These should be all the objects you'll ever need:
"""
import logging as _logging
import os as _os

from cpy2py.meta import __version__
from cpy2py.utility.compat import NullHandler
from cpy2py.proxy.proxy_object import TwinObject
from cpy2py.twinterpreter.twin_master import TwinMaster
from cpy2py.twinterpreter import kernel_state


_base_logger = _logging.getLogger('__cpy2py__')
_base_logger.propagate = False
# debugging logger to stderr
if _os.environ.get('CPY2PY_DEBUG'):
    _base_logger.addHandler(_logging.StreamHandler())
else:
    _base_logger.addHandler(NullHandler())

__all__ = ['TwinObject', 'TwinMaster', 'kernel_state', '__version__']
