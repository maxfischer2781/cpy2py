"""
Instances of :py:class:`~.MainDef` define how ``__main__`` is
bootstrapped in twinterpreters. A
:py:class:`~cpy2py.twinterpeter.twin_master.TwinMaster` without
a :py:class:`~.MainDef` defaults to :py:data:`DEFAULT_DEF`.

Bootstrap the ``__main__`` module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``__main__`` module is the starting point of every python script or
application. Bootstrapping it into twinterpreters allows the recreation
of a similar environment without explicitly using :py:mod:`~cpy2py`.

In addition, smaller scripts may *only* consist of a
single script/module/file. Bootstrapping ``__main__`` gives twinterpreters
direct access to objects of this script. This is required to dispatch any
object defined only in the script.

Since ``__main__`` may have side effects and require adjustments for
different interpreters, it is not safe to execute it unconditionally.
The default is to bootstrap ``__main__`` as a module, which should be
safe for properly written applications.

Defining the ``__main__`` module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The parameter ``main_module`` identifies the ``__main__`` module for
lookup in a twinterpreter.
It may be specified explicitly, automatically detected or turned off.

**File Path**
  Filesystem path to a module to execute, e.g. "/foo/bar.py". Will be
  run like invoking "python /foo/bar.py". Useful for an absolute
  definition of ``__main__`` across all twinterpreters.

**Module Name**
  Python module name/path to a module to execute, e.g. "foo.bar". Will be
  run like invoking "python -m foo.bar". Useful for interpreter-specific
  definitions of ``__main__``, e.g. respecting different python versions.

:py:attr:`~.MainDef.FETCH_PATH`
  Use the file path of ``__main__``.

:py:attr:`~.MainDef.FETCH_NAME`
  Use the module name of ``__main__``.

:py:const:`True`
  Try using :py:attr:`FETCH_NAME` if possible. Otherwise, use :py:attr:`FETCH_PATH`.

:py:const:`None`
  Do not bootstrap ``__main__``.

Execution of the ``__main__`` module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setting ``run_main`` defines whether ``__main__`` is actually executed as a script;
that is, it satisfies ``__name__ == "__main__"``. Active code in ``__main__`` should
usually be guarded against running when imported as a module.

In most cases, twinterpreters and other elements are likely created from active code
in ``__main__``. Rerunning this in twinterpreters would duplicate such elements. The
default is thus to avoid executing such code again.

However, the simplest method of creating the same environment across twinterpreters
is to have ``__main__`` be aware of whether its run in the master or not. If this is
the case, setting ``run_main=True`` avoids the need to explicitly
use initializers/finalizers.
"""
import sys
import os
import runpy
import types


class MainDef(object):
    """
    Definition on bootstrapping a program into a twinterpreter

    :param main_module: module path, name or directive to fetch ``__main__``
    :type main_module: str, bool or None
    :param run_main: bootstrap ``__main__`` with ``__name__ == "__main__"``
    :type run_main: bool
    :param restore_argv: whether to replicate the parent ``sys.argv``
    :type restore_argv: bool
    """
    FETCH_PATH = "Use __main__ via absolute path"
    FETCH_NAME = "Use __main__ via module name"

    def __init__(self, main_module=True, run_main=False, restore_argv=False):
        self.main_module = main_module
        self.run_main = run_main
        self._argv = None  # argv EXCLUDING first element (executable name)
        self.restore_argv = restore_argv

    def _resolve_main(self, main_module):
        if main_module is True:
            try:
                return self._get_main_name()
            except ValueError:
                return os.path.abspath(sys.modules['__main__'].__file__)
        if main_module == self.FETCH_PATH:
            return os.path.abspath(sys.modules['__main__'].__file__)
        elif main_module == self.FETCH_NAME:
            return self._get_main_name()
        return main_module

    @staticmethod
    def _get_main_name():
        """
        Get the module name of ``__main__``

        :raises: :py:exc:`ValueError` if ``__main__`` does not provide its name
        :returns: full module/package name of ``__main__``
        """
        main = sys.modules['__main__']
        try:
            return main.__spec__.name
        except AttributeError:
            pass
        try:
            package, name = main.__package__, os.path.splitext(os.path.basename(main.__file__))[0]
            if package is None and os.path.abspath(os.path.dirname(main.__file__)) != os.path.abspath(os.getcwd()):
                raise AttributeError
        except AttributeError:
            raise ValueError("Cannot derive path if __main__ not run as module/package (see 'python -m')")
        else:
            return (package + '.' + name) if package else name

    def __getstate__(self):
        return {
            'main_module': self._resolve_main(self.main_module),
            'run_main': self.run_main,
            'restore_argv': self.restore_argv,
            '_argv': sys.argv[1:] if self.restore_argv else [],
        }

    def bootstrap(self):
        # all of these are set by unpickling in a spawning child process
        assert self.main_module != self.FETCH_NAME and self.main_module != self.FETCH_PATH and self._argv is not None,\
            "Cannot bootstrap sys.argv in initial environment"
        if self.restore_argv:
            sys.argv[1:] = self._argv[:]
        if self.main_module is None:
            self._bootstrap_none()
        elif os.path.exists(self.main_module):
            self._bootstrap_path(str(self.main_module))
        else:
            self._bootstrap_name(str(self.main_module))

    @staticmethod
    def _bootstrap_none():
        sys.modules['__cpy2py_main__'] = sys.modules['__cpy2py_bootstrap__'] = sys.modules['__main__']

    def _bootstrap_path(self, main_path):
        # ipython - see https://github.com/ipython/ipython/issues/4698
        # utrunner - PyCharm unittests
        if os.path.splitext(os.path.basename(main_path))[0] in ('ipython', 'utrunner'):
            return self._bootstrap_none()
        main_name = '__main__' if self.run_main else '__cpy2py_main__'
        main_dict = runpy.run_path(main_path, run_name=main_name)
        self._bootstrap_set_main(main_dict)

    def _bootstrap_name(self, mod_name):
        # guard against running __main__ files of packages
        if not self.run_main and (mod_name == "__main__" or mod_name.endswith(".__main__")):
            return self._bootstrap_none()
        main_name = '__main__' if self.run_main else '__cpy2py_main__'
        main_dict = runpy.run_module(mod_name, run_name=main_name, alter_sys=True)
        self._bootstrap_set_main(main_dict)

    @staticmethod
    def _bootstrap_set_main(main_dict):
        sys.modules['__cpy2py_bootstrap__'] = sys.modules['__main__']
        main_module = types.ModuleType('__cpy2py_main__')
        main_module.__dict__.update(main_dict)
        sys.modules['__main__'] = sys.modules['__cpy2py_main__'] = main_module

    def __repr__(self):
        return "%s(main_module=%r, run_main=%r)" % (self.__class__.__name__, self.main_module, self.run_main)

    def __eq__(self, other):
        try:
            return self.main_module == other.main_module\
                and self.run_main == other.run_main
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        return not self == other

#: The default :py:class:`MainDef` instance to use
DEFAULT_DEF = MainDef()
