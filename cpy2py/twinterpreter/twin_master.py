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
import os
import errno
import threading
import time
import logging

from cpy2py.kernel import kernel_state
from cpy2py.twinterpreter import bootstrap
from cpy2py.ipyc import ipyc_fifo

from .twin_def import TwinDef
from .twin_main import MainDef


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

    def __new__(
            cls, executable=None, twinterpreter_id=None, kernel=None, main_module=True, run_main=None,
            restore_argv=False, ipyc=ipyc_fifo.DuplexFifoIPyC
    ):
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

    def __init__(
            self, executable=None, twinterpreter_id=None, kernel=None, main_module=True, run_main=None,
            restore_argv=False, ipyc=ipyc_fifo.DuplexFifoIPyC
    ):
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
        self.ipyc = ipyc

    @property
    def executable(self):
        """Executable used to launch a twinterpreter"""
        return self.twin_def.executable

    @property
    def twinterpreter_id(self):
        """Identifier of a twinterpreter"""
        return self.twin_def.twinterpreter_id

    @property
    def native(self):
        """Whether the master defines its own controlling scope"""
        return kernel_state.is_twinterpreter(self.twinterpreter_id)

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
            "Client, Server and Process must have been realeased together"
        return False

    def start(self):
        """
        Start the twinterpeter if it is not alive

        :returns: whether the twinterpeter is alive
        """
        if self.native:
            return True
        if self._master_store.get(self.twinterpreter_id) is not self:
            raise RuntimeError("Attempt to start TwinMaster after destroying it")
        if not self.is_alive:
            self._logger.warning('<%s> Starting Twin [%s]', kernel_state.TWIN_ID, self.twinterpreter_id)
            my_server_ipyc = self.ipyc()
            my_client_ipyc = self.ipyc()
            self._process = self.twin_def.spawn(
                cli_args=self._twin_args(my_client_ipyc=my_client_ipyc, my_server_ipyc=my_server_ipyc),
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
        if self.native:
            return call(*call_args, **call_kwargs)
        assert self._kernel_client is not None
        return self._kernel_client.request_dispatcher.dispatch_call(call, *call_args, **call_kwargs)
