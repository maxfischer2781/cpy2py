.. # - # Copyright 2016 Max Fischer
.. # - #
.. # - # Licensed under the Apache License, Version 2.0 (the "License");
.. # - # you may not use this file except in compliance with the License.
.. # - # You may obtain a copy of the License at
.. # - #
.. # - #     http://www.apache.org/licenses/LICENSE-2.0
.. # - #
.. # - # Unless required by applicable law or agreed to in writing, software
.. # - # distributed under the License is distributed on an "AS IS" BASIS,
.. # - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. # - # See the License for the specific language governing permissions and
.. # - # limitations under the License.

++++++
CPy2Py
++++++

|pypi| |landscape| |travis| |codecov|

Multi-intepreter execution environment

`cpy2py` allows multiple interpreters to act as one application. In parallel
to the main interpreter, other interpreters are run to execute parts of
the application.

.. |landscape| image:: https://landscape.io/github/maxfischer2781/cpy2py/master/landscape.svg?style=flat
   :target: https://landscape.io/github/maxfischer2781/cpy2py/master
   :alt: Code Health

.. |travis| image:: https://travis-ci.org/maxfischer2781/cpy2py.svg?branch=master
    :target: https://travis-ci.org/maxfischer2781/cpy2py
    :alt: Test Health

.. |pypi| image:: https://img.shields.io/pypi/v/cpy2py.svg
    :target: https://pypi.python.org/pypi/cpy2py
    :alt: PyPI Package

.. |codecov| image:: https://codecov.io/gh/maxfischer2781/cpy2py/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/maxfischer2781/cpy2py
  :alt: Code Coverage

.. contents:: **Table of Contents**
    :depth: 2

Quick Guide
===========

Twinterpreters and TwinMasters
------------------------------

A twinterpreter is simply another interpreter running as a subprocess -
with some glue and magic sprinkled on it. You can control and create them
using a :py:class:`cpy2py.TwinMaster`.

You should only ever worry about two methods: :py:meth:`TwinMaster.start`
launches the twinterpreter. :py:meth:`TwinMaster.execute` executes
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

You create twins by inheriting from
:py:class:`cpy2py.TwinObject` instead of :py:class:`object` and
setting a ``__twin_id__``. That's it.

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

If you don't set ``__twin_id__`` on a child of
:py:class:`cpy2py.TwinObject`,
the class will always be native to the main interpreter. Handy for all
the stuff that's needed everywhere but really doesn't belong anywhere.

:note: At the moment, you have to explicitly start a class's native
       twinterpreter before instantiating the class. Only the main
       interpreter is always available, of course.

Debugging
---------

The core of :py:mod:`cpy2py` supports some :py:mod:`logging` facilities.
All such loggers are children of the ``__cpy2py__`` logger. By default,
no active handlers are attached and propagation is disabled. If needed,
you reconfigure them like any other :py:mod:`logging` logger to suit your
needs.
Note that if python is run with the `-O` flag, several logging calls are
skipped entirely to improve performance.


For small scale debugging, one can set the environment variable
:envvar:`CPY2PY_DEBUG`. If it is defined and not empty, logging output
is written to `stderr`. In addition, if it names a valid :py:mod:`logging`
level, that logging level is used.

Note that loggers are meant for development and only address the internal
state. Your application should not depend on this information. Unless
:py:mod:`cpy2py` misbehaves (or you suspect it to), ignore its logging.

Current Status
==============

CPy2Py is stable at its core, but still has some features missing.
What's there is more than sufficient to significantly enhance your applications.

Features
--------

* Seamlessly integrates into python code.

  * All internals are wrapped away behind the plain python interfaces.
    No eval, exec or code strings required.

  * Lightweight hooks optimize objects and functions for use with :py:mod:`cpy2py`.

  * If needed, **any** pickle'able callable can be dispatched to another interpreter.

* Objects natively integrate with twinterpreters.

  * Objects can live in a specific interpreter, with proxies replacing them in others.
    Classes and instances transparently interact with :py:mod:`cpy2py` in the background.

  * Both class and instance attributes work as expected.
    Methods, classmethods, staticmethods and descriptors are fully supported.

  * Inheritance is fully supported, including multiple inheritance.
    Affiliation to interpreters can be changed freely.

* A wide range of interpeters is supported.

  * Pure python, no dependencies means perfect portability.

  * Any interpeter compatible with python 2.6 to 3.5 is supported.

  * Virtual Environments work out of the box.

  * Tested with cpython and pypy, on Linux and Mac OSX.

Gotchas/Limitations
-------------------

* Calls across interpreters are blocking and not threadsafe.
  If recursion switches between twinterpreters, :py:class:`cpy2py.TwinMaster` must use the ``'async'`` kernel.

* Module level settings are not synchronized.
  For example, configuration of :py:mod:`logging` is not applied to twinterpreters.
  Use :py:class:`~cpy2py.twinterpreter.group_state.TwinGroupState` for initialisation, or write modules aware of twinterpreters.

* A :py:mod:`weakref` to objects only takes local references into account, not cross-interpreter references.

Performance
-----------

Dispatching to another twinterpreter adds about 200 - 300 us of overhead.
This is mainly due to serialization for the IPC between the interpreters.
Using the asynchronous kernel, there is an additional overhead for creating threads.

In general, twinterpreters get faster the shorter they have to wait between requests.
``pypy`` twinterpreters benefit from a high number of requests, allowing their JIT to warm up.
Python3 connections are the fastest, provided that both twinterpreters support pickle protocol 4.

You can benchmark the overhead yourself using the :py:mod:`cpy2py_benchmark` tools.

==================== ==================== ==================== ====================
               pypy2               15x15k                30x5k                300x1
==================== ==================== ==================== ====================
               pypy2        187 ±  1.5 us        228 ±  2.5 us        505 ± 51.8 us
               pypy3        165 ±  1.3 us        209 ±  2.4 us        402 ±  8.0 us
           python2.7        178 ±  0.6 us        139 ±  0.3 us        239 ±  7.6 us
           python3.4        149 ±  0.4 us        118 ±  0.2 us        258 ±  8.0 us
==================== ==================== ==================== ====================
