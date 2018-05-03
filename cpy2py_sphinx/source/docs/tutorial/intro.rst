Getting started: A simple application
=====================================

Running an application using :py:mod:`cpy2py` requires only regular Python workflows.
The catch is that you must prepare (at least) two Python environments for your application.
However, this mainly boils down to installing the proper dependencies in the proper environment.

A common use case for :py:mod:`cpy2py` is to bridge the fast PyPy with the extensible CPython.
This example uses ``pypy3`` and ``python3`` to run a single application.

Preparing your environment
--------------------------

In order for two interpreters to communicate, *both* must have :py:mod:`cpy2py` installed.
This can be done using ``pip`` for each interpreter:

.. code:: bash

    python3 -m pip install cpy2py --user
    pypy3 -m pip install cpy2py --user

That's it!
Your interpreters are now both ready to run your application.

Interlude: Torturing the CPU
----------------------------

To begin, we write an application *without* using :py:mod:`cpy2py`.
This is a naive number cruncher that runs well in PyPy, but slow in CPython:

.. code:: python

    # file cpy2py_demo.py
    def sum_series(max_n):
        return [
            (n, sum(range(n)))
            for n in range(0, max_n + 1, max_n // 10)
        ]

    if __name__ == "__main__":
        for n, total in sum_series(50000000):
            print(n, '=>', total)

Give it a try with both PyPy and CPython;
the later should be significantly slower.

.. code:: bash

    pypy3 cpy2py_demo.py
    python3 cpy2py_demo.py

:note: If the example is too fast or slow for your liking, adjust the ``max_n`` parameter.

Pinning a function to an interpreter
------------------------------------

It is obvious that performance differences are due to ``sum_series``; the ``print`` loop is negligible.
Thus, we want ``sum_series`` to always execute with PyPy.
Ideally, the remaining application remains untouched by this optimisation.

We can pin ``sum_series`` to an interpreter using :py:func:`cpy2py.twinfunction`.
For simplicity, we use the executable name ``"pypy3"`` to both identify and call the interpreter:

.. code:: python

    # file cpy2py_demo.py, version 2
    from cpy2py import twinfunction


    @twinfunction('pypy3')
    def sum_series(max_n):
        return [
            (n, sum(range(n)))
            for n in range(0, max_n + 1, max_n // 10)
        ]

    if __name__ == "__main__":
        for n, total in sum_series(50000000):
            print(n, '=>', total)

This is enough to have ``sum_series`` be executed in PyPy.
When called from CPython, the function is offloaded to a second interpreter.
You should see a significant speedup when executing the script with CPython.

Epilogue: No Free Lunch
-----------------------

You may notice that running your script directly with ``pypy3`` is *slower* after adding :py:mod:`cpy2py`.
This is because :py:mod:`cpy2py` has to setup an extensive bookkeeping infrastructure.

======== ======== =====
Runtime  CPython3 PyPy3
======== ======== =====
unpinned  6.9s     0.4s
pinned    1.2s     0.8s
======== ======== =====

While this overhead will likely be reduced in the future, it will always be notable for short scripts.
Make sure the use of :py:mod:`cpy2py` is beneficial or required before applying it.
