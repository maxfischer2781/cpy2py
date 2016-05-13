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
import subprocess
import os
import errno
import threading
import time
import sys
import types
import runpy
import logging

from cpy2py.kernel import kernel_single, kernel_state, kernel_async, kernel_multi
from cpy2py.twinterpreter import bootstrap
from cpy2py.ipyc import ipyc_fifo
from cpy2py.utility import proc_tools
from cpy2py.utility.compat import stringabc


class TwinDef(object):
    """
    Definition of a twinterpreter

    This is a helper to resolve defaults. It also automatically extracts
    configuration parameters.

    :param executable: path or name of the interpeter executable
    :type executable: str
    :param twinterpreter_id: identifier for the twin
    :type twinterpreter_id: str
    :param kernel: the type of kernel to deploy
    :type kernel: module or tuple

    For simplicity, it is sufficient to supply either ``executable`` or
    ``twinterpreter_id``. In this case, ``twinterpreter_id`` is assumed to be
    the basename of `executable`.

    If given or derived, ``executable`` must point to a python interpreter. This
    includes interpreters created by `virtualenv <https://virtualenv.pypa.io/>`_.
    The interpreter can be specified as an absolute path, a relative path or a
    name to lookup in :envvar:`PATH`.

    Since it impacts performance, one may decide to use a different ``kernel``.
    Three methods for specifying the ``kernel`` are available:

    * tuple of ``(client, server)``

    * module providing ``mod.CLIENT`` and ``mod.SERVER``

    * key to an element of :py:attr:`default_kernels`

    Only one kernel may use a specific ``twinterpreter_id`` at any time. For
    simplicity, one may "create" the same :py:class:`~.TwinMaster` multiple times;
    the class works like a singleton in this case.
    """
    default_kernels = {
        'single': kernel_single,
        'async': kernel_async,
        'multi': kernel_multi,
    }

    def __init__(self, executable=None, twinterpreter_id=None, kernel=None):
        if isinstance(executable, self.__class__):
            assert twinterpreter_id is None and kernel is None, "Mixing cloning and explicit assignment"
            executable, twinterpreter_id, kernel = executable.executable, executable.twinterpreter_id, executable.kernel
        # Resolve incomplete argument list using defaults
        assert executable is not None or twinterpreter_id is not None,\
            "At least one of 'executable' and 'twinterpreter_id' must be set"
        if twinterpreter_id is None:
            twinterpreter_id = os.path.basename(executable)
            executable = proc_tools.get_executable_path(executable)
        elif executable is None:
            executable = proc_tools.get_executable_path(twinterpreter_id)
        else:
            executable = proc_tools.get_executable_path(executable)
        self.executable = executable
        self.twinterpreter_id = twinterpreter_id
        self.pickle_protocol = proc_tools.get_best_pickle_protocol(self.executable)
        self.kernel_client, self.kernel_server = self._resolve_kernel_arg(kernel)

    @property
    def kernel(self):
        return self.kernel_client, self.kernel_server

    def _resolve_kernel_arg(self, kernel_arg):
        kernel_arg = kernel_arg or 'single'
        kernel_arg = self.default_kernels.get(kernel_arg, kernel_arg)
        try:
            client, server = kernel_arg
        except (TypeError, ValueError):
            try:
                client, server = kernel_arg.CLIENT, kernel_arg.SERVER
            except AttributeError:
                raise ValueError("Expected 'kernel' to reference client and server")
        return client, server

    def __eq__(self, other):
        try:
            return self.executable == other.executable\
                and self.twinterpreter_id == other.twinterpreter_id\
                and self.kernel == other.kernel
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        return not self == other


class MainDef(object):
    """
    Definition on how to bootstrap ``__main__``

    :param main_module: module path, name or directive to fetch ``__main__``
    :type main_module: str, bool or None
    :param run_main: bootstrap ``__main__`` with ``__name__ == "__main__"``
    :type run_main: bool
    :param restore_argv: whether to replicate the parent ``sys.argv``
    :type restore_argv: bool

    The paremeter ``main_module`` identifies the ``__main__`` module for future lookup.
    It can be specified explicitly, or set to automatic detection.

    File Path
      Filesystem path to a module to execute, e.g. "/foo/bar.py". Will be
      run like invoking "python /foo/bar.py".

    Module Name
      Python module name/path to a module to execute, e.g. "foo.bar". Will be
      run like invoking "python -m foo.bar".

    :py:attr:`FETCH_PATH`
      Use the file path of ``__main__``.

    :py:attr:`FETCH_NAME`
      Use the module name of ``__main__``.

    :py:const:`True`
      Try using :py:attr:`FETCH_NAME` if possible. Otherwise, use :py:attr:`FETCH_PATH`.

    :py:const:`None`
      Do not bootstrap ``__main__``.

    Setting ``run_main`` defines whether ``__main__`` is actually executed as a script;
    that is, it satisfies ``__name__ == "__main__"``. Active code in ``__main__`` should
    usually be guarded against running when imported as a module.

    In most cases, twinterpreters and other elements are likely created from active code
    in ``__main__``. Rerunning this in twinterpreters would duplicate such elements. The
    default is thus to avoid executing such code again.
    """
    FETCH_PATH = "Use __main__ via absolute path"
    FETCH_NAME = "Use __main__ via module name"

    def __init__(self, main_module=True, run_main=False, restore_argv=False):
        self.main_module = main_module
        self.run_main = run_main
        self._argv = []  # argv EXCLUDING first element (executable name)
        self.restore_argv = restore_argv

    @property
    def restore_argv(self):
        return bool(self._argv)

    @restore_argv.setter
    def restore_argv(self, value):
        if value:
            self._argv = sys.argv[1:]
        else:
            self._argv = []

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
            '_argv': self._argv,
        }

    def bootstrap(self):
        assert self.main_module != self.FETCH_NAME and self.main_module != self.FETCH_PATH
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


class TwinMaster(object):
    """
    Manager for a twinterpeter

    Spawns, configures and supervises the actual interpeter process. In order to
    use any twinterpeters, a corresponding TwinMaster must be created and its
    :py:meth:`TwinMaster.start` method called.

    :see: :py:class:`~.TwinDef` and :py:class:`~.MainDef` for parameters and their meaning.
    """
    _initialized = False

    #: singleton store `twinterpreter_id` => `master`
    _master_store = {}

    def __new__(cls, executable=None, twinterpreter_id=None, kernel=None, main_module=True, run_main=None,
                restore_argv=False):
        twin_def = TwinDef(executable, twinterpreter_id, kernel)
        try:
            master = cls._master_store[twin_def.twinterpreter_id]
        except KeyError:
            self = object.__new__(cls)
            cls._master_store[twin_def.twinterpreter_id] = self
            return self
        else:
            main_def = MainDef(main_module, run_main, restore_argv)
            assert master.twin_def == twin_def and master.main_def == main_def, \
                "interpreter with same twinterpreter_id but different settings already exists"
            return master

    def __init__(self, executable=None, twinterpreter_id=None, kernel=None, main_module=True, run_main=None,
                 restore_argv=False):
        # avoid duplicate initialisation of singleton
        if self._initialized:
            return
        self._initialized = True
        self.twin_def = TwinDef(executable, twinterpreter_id, kernel)
        self.main_def = MainDef(main_module, run_main, restore_argv)
        self._logger = logging.getLogger(
            '__cpy2py__.twin.%s_to_%s.master' % (kernel_state.TWIN_ID, self.twinterpreter_id)
        )
        self._process = None
        self._kernel_server = None
        self._kernel_client = None
        self._server_thread = None

    @property
    def executable(self):
        """Executable used to launch a twinterpreter"""
        return self.twin_def.executable

    @property
    def twinterpreter_id(self):
        """Identifier of a twinterpreter"""
        return self.twin_def.twinterpreter_id

    @property
    def is_alive(self):
        """Whether the twinterpeter process is alive"""
        if self._process is not None:
            try:
                os.kill(self._process.pid, 0)
            except OSError as err:
                if err.errno == errno.EPERM:  # not allowed to kill EXISTING process
                    return True
                if err.errno != errno.ESRCH:
                    raise
                # no such process anymore, cleanup
                self._cleanup()
                return False
            else:
                return True
        assert self._process == self._kernel_client == self._kernel_server,\
            "Client, Server and Process must have been realease together"
        return False

    def start(self):
        """
        Start the twinterpeter if it is not alive

        :returns: whether the twinterpeter is alive
        """
        if self._master_store.get(self.twinterpreter_id) is not self:
            raise RuntimeError("Attempt to start TwinMaster after destroying it")
        if not self.is_alive:
            self._logger.warning('<%s> Starting Twin [%s]', kernel_state.TWIN_ID, self.twinterpreter_id)
            my_server_ipyc = ipyc_fifo.DuplexFifoIPyC()
            my_client_ipyc = ipyc_fifo.DuplexFifoIPyC()
            self._process = subprocess.Popen(
                self._twin_args(my_client_ipyc=my_client_ipyc, my_server_ipyc=my_server_ipyc),
                env=self._twin_env()
            )
            self._kernel_client = self.twin_def.kernel_client(
                self.twin_def.twinterpreter_id,
                ipyc=my_client_ipyc,
                pickle_protocol=self.twin_def.pickle_protocol,
            )
            self._kernel_server = self.twin_def.kernel_server(
                self.twin_def.twinterpreter_id,
                ipyc=my_server_ipyc,
                pickle_protocol=self.twin_def.pickle_protocol,
            )
            self._server_thread = threading.Thread(target=self._kernel_server.run)
            self._server_thread.daemon = True
            self._server_thread.start()
            # finalize the twinterpreter
            kernel_state.TWIN_GROUP_STATE.run_finalizers(self.twinterpreter_id)
            self._logger.info('<%s> Initialized Twin [%s]', kernel_state.TWIN_ID, self.twinterpreter_id)
        else:
            self._logger.warning('<%s> Reusing Twin [%s]', kernel_state.TWIN_ID, self.twinterpreter_id)
        return self.is_alive

    def _twin_args(self, my_client_ipyc, my_server_ipyc):
        """Create the twin's CLI args"""
        twin_args = []
        # twinterpreter invocation
        if isinstance(self.executable, stringabc):
            # bare interpreter - /foo/bar/python
            twin_args.append(self.executable)
        else:
            # invoked interpreter - [ssh foo@bar python] or [which python]
            twin_args.extend(self.executable)
        # preserve -O
        if not __debug__:
            twin_args.append('-O')
        # bootstrap
        twin_args.extend([
            '-m', 'cpy2py.twinterpreter.bootstrap',
            '--peer-id', kernel_state.TWIN_ID,
            '--twin-id', self.twinterpreter_id,
            '--master-id', kernel_state.MASTER_ID,
            '--server-ipyc', bootstrap.dump_connector(my_client_ipyc.connector),
            '--client-ipyc', bootstrap.dump_connector(my_server_ipyc.connector),
            '--ipyc-pkl-protocol', str(self.twin_def.pickle_protocol),
            '--kernel', bootstrap.dump_kernel(*self.twin_def.kernel),
            '--main-def', bootstrap.dump_main_def(self.main_def),
            '--cwd', os.getcwd(),
            '--initializer',
        ] + bootstrap.dump_initializer(kernel_state.TWIN_GROUP_STATE.initializers))
        return twin_args

    def _twin_env(self):
        """Create the twin's starting environment"""
        twin_env = os.environ.copy()
        twin_env['__CPY2PY_TWIN_ID__'] = self.twinterpreter_id
        twin_env['__CPY2PY_MASTER_ID__'] = kernel_state.MASTER_ID
        return twin_env

    def stop(self):
        """Terminate the twinterpreter"""
        self._cleanup()
        return self.is_alive

    def destroy(self):
        """Stop any twinterpreter and cleanup the master"""
        self.stop()
        del self._master_store[self.twinterpreter_id]
        self._logger.info('<%s> Destroyed Twin [%s]', kernel_state.TWIN_ID, self.twinterpreter_id)

    def _cleanup(self):
        """Try and close all connections"""
        if self._kernel_client is not None and self._kernel_client.stop():
            self._kernel_client = None
            self._logger.info('<%s> Cleaned up Twin Client [%s]', kernel_state.TWIN_ID, self.twinterpreter_id)
        if self._process is not None:
            # allow twin to shut down before killing it outright
            shutdown_time = time.time()
            while self._process.poll() is None:
                time.sleep(0.1)
                if time.time() - shutdown_time > 5:
                    self._process.kill()
            if self._process.poll() is not None:
                self._process = None
                self._logger.info('<%s> Cleaned up Twin Process [%s]', kernel_state.TWIN_ID, self.twinterpreter_id)
        # reap server LAST in case twin shutdown needs it
        if self._kernel_server is not None and self._kernel_server.stop():
            self._kernel_server = None
            self._logger.info('<%s> Cleaned up Twin Server [%s]', kernel_state.TWIN_ID, self.twinterpreter_id)

    def execute(self, call, *call_args, **call_kwargs):
        """
        Invoke a callable

        :param call: callable to invoke
        :type call: callable
        :param call_args: positional arguments to `call`
        :param call_kwargs: keyword arguments to `call`
        :returns: result of `call(*call_args, **call_kwargs)`
        """
        assert self._kernel_client is not None
        return self._kernel_client.request_dispatcher.dispatch_call(call, *call_args, **call_kwargs)
