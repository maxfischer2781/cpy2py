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

from cpy2py.kernel import kernel_single, kernel_state, kernel_async
from cpy2py.twinterpreter import bootstrap
from cpy2py.ipyc import ipyc_fifo
from cpy2py.utility import proc_tools


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
                raise ValueError("Expected 'kernel' to be a (client, server) tuple or module exposing CLIENT and SERVER")
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


class TwinMaster(object):
    """
    Manager for a twinterpeter

    Spawns, configures and supervises the actual interpeter process. In order to
    use any twinterpeters, a corresponding TwinMaster must be created and its
    :py:meth:`TwinMaster.start` method called.

    :see: :py:class:`~.TwinDef` for parameters and their interpretation.
    """
    _initialized = False

    #: singleton store `twinterpreter_id` => `master`
    _master_store = {}

    def __new__(cls, executable=None, twinterpreter_id=None, kernel=None):
        twin_def = TwinDef(executable, twinterpreter_id, kernel)
        try:
            master = cls._master_store[twin_def.twinterpreter_id]
        except KeyError:
            self = object.__new__(cls)
            cls._master_store[twin_def.twinterpreter_id] = self
            return self
        else:
            assert master.twin_def == twin_def,\
                "interpreter with same twinterpreter_id but different settings already exists"
            return master

    def __init__(self, executable=None, twinterpreter_id=None, kernel=None):
        # avoid duplicate initialisation of singleton
        if self._initialized:
            return
        self._initialized = True
        self.twin_def = TwinDef(executable, twinterpreter_id, kernel)
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
        return False

    def start(self):
        """
        Start the twinterpeter if it is not alive

        :returns: whether the twinterpeter is alive
        """
        if self._master_store.get(self.twinterpreter_id) is not self:
            raise RuntimeError("Attempt to start TwinMaster after destroying it")
        if not self.is_alive:
            my_server_ipyc = ipyc_fifo.DuplexFifoIPyC()
            my_client_ipyc = ipyc_fifo.DuplexFifoIPyC()
            self._process = subprocess.Popen(
                [
                    self.twin_def.executable, '-m', 'cpy2py.twinterpreter.bootstrap',
                    '--peer-id', kernel_state.TWIN_ID,
                    '--twin-id', self.twin_def.twinterpreter_id,
                    '--master-id', kernel_state.MASTER_ID,
                    '--server-ipyc', bootstrap.dump_connector(my_client_ipyc.connector),
                    '--client-ipyc', bootstrap.dump_connector(my_server_ipyc.connector),
                    '--ipyc-pkl-protocol', str(self.twin_def.pickle_protocol),
                    '--kernel', bootstrap.dump_kernel(*self.twin_def.kernel),
                    '--initializer',
                ] + bootstrap.dump_initializer(kernel_state.TWIN_GROUP_STATE.initializers),
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
        return self.is_alive

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

    def _cleanup(self):
        """Try and close all connections"""
        if self._kernel_client is not None and self._kernel_client.stop():
            self._kernel_client = None
        if self._kernel_server is not None and self._kernel_server.stop():
            self._kernel_server = None
        if self._process is not None:
            self._process.kill()
            time.sleep(0.1)
            if self._process.poll() is not None:
                self._process = None

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
