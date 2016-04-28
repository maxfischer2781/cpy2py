"""
The kernel is the main thread of execution running inside a twinterpreter.

Any connection between twinterpreters is handled by two kernels. Each
consists of client and server side residing in the different interpreters.

The kernels assume that they have been setup properly. Use
:py:class:`~cpy2py.twinterpreter.twin_master.TwinMaster` start kernel pairs.
"""
