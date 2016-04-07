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

import cpy2py.twinterpreter.kernel_state
import cpy2py.twinterpreter.kernel
from cpy2py.twinterpreter import bootstrap
from cpy2py.ipyc import ipyc_fifo
from cpy2py.utility import proc_tools


class TwinMaster(object):
    """
    Manager for a twinterpeter

    Spawns, configures and supervises the actual interpeter process. In order to
    use any twinterpeters, a corresponding TwinMaster must be created and its
    :py:meth:`TwinMaster.start` method called.

    :param executable: path or name of the interpeter executable
    :type executable: str
    :param twinterpreter_id: identifier for the twin
    :type twinterpreter_id: str

    :note: For simplicity, it is sufficient to supply either `executable` or
           `twinterpreter_id`. In this case, `twinterpreter_id` is assumed to be
           the basename of `executable`.

    :note: The attributes :py:attr:`executable` and :py:attr:`twinterpreter_id`
           act as defaults if *neither* `executable` nor `twinterpreter_id` is
           provided at instantiation. They are meant for subclassing to provide
           default Masters.

    :note: Only one kernel may use a specific `twinterpreter_id` at any time.
    """
    #: default executable
    executable = None
    #: default twin id
    twinterpreter_id = None
    #: singleton store `twinterpreter_id` => `master`
    _master_store = {}

    def __new__(cls, executable=None, twinterpreter_id=None):
        executable, twinterpreter_id = cls._default_args(executable, twinterpreter_id)
        try:
            master = cls._master_store[twinterpreter_id]
        except KeyError:
            self = object.__new__(cls)
            cls._master_store[twinterpreter_id] = self
            return self
        else:
            assert master.executable == executable,\
                "interpreter with same twinterpreter_id but different executable already exists"
            return master

    def __init__(self, executable=None, twinterpreter_id=None):
        # avoid duplicate initialisation of singleton
        if hasattr(self, '_init'):
            return
        self._init = True
        self.executable, self.twinterpreter_id = self._default_args(executable, twinterpreter_id)
        self._process = None
        self._kernel = None
        self._server_thread = None
        self._pkl_protocol = proc_tools.get_best_pickle_protocol(self.executable)

    @classmethod
    def _default_args(cls, executable, twinterpreter_id):
        """Resolve incomplete argument list using defaults"""
        if executable is not None and twinterpreter_id is not None:
            return executable, twinterpreter_id
        elif executable is None and twinterpreter_id is None:
            return cls.executable, cls.twinterpreter_id
        elif executable is not None:
            twinterpreter_id = os.path.basename(executable)
            executable = proc_tools.get_executable_path(executable)
        else:
            twinterpreter_id = twinterpreter_id
            executable = proc_tools.get_executable_path(twinterpreter_id)
        return executable, twinterpreter_id

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
                self._process = None
                self._kernel = None
                return False
            else:
                return True
        return False

    def start(self):
        """
        Start the twinterpeter if it is not alive

        :returns: whether the twinterpeter is alive
        """
        if not self.is_alive:
            my_server_ipyc = ipyc_fifo.DuplexFifoIPyC()
            my_client_ipyc = ipyc_fifo.DuplexFifoIPyC()
            self._process = subprocess.Popen(
                [
                    self.executable, '-m', 'cpy2py.twinterpreter.bootstrap',
                    '--peer-id', cpy2py.twinterpreter.kernel_state.TWIN_ID,
                    '--twin-id', self.twinterpreter_id,
                    '--master-id', cpy2py.twinterpreter.kernel_state.MASTER_ID,
                    '--server-ipyc', bootstrap.dump_connector(my_client_ipyc.connector),
                    '--client-ipyc', bootstrap.dump_connector(my_server_ipyc.connector),
                    '--ipyc-pkl-protocol', str(self._pkl_protocol),
                ]
            )
            self._kernel = cpy2py.twinterpreter.kernel.SingleThreadKernel(
                self.twinterpreter_id,
                server_ipyc=my_server_ipyc,
                client_ipyc=my_client_ipyc,
                pickle_protocol=self._pkl_protocol,
            )
            self._server_thread = threading.Thread(target=self._kernel.run)
            self._server_thread.daemon = True
            self._server_thread.start()
        return self.is_alive

    def stop(self):
        """Terminate the twinterpreter"""
        if self._kernel is not None:
            if self._kernel.stop():
                self._kernel = None
                self._process = None
        return self.is_alive

    def execute(self, call, *call_args, **call_kwargs):
        """
        Invoke a callable

        :param call: callable to invoke
        :type call: callable
        :param call_args: positional arguments to `call`
        :param call_kwargs: keyword arguments to `call`
        :returns: result of `call(*call_args, **call_kwargs)`
        """
        assert self._kernel is not None
        return self._kernel.dispatch_call(call, *call_args, **call_kwargs)
