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
from __future__ import absolute_import
import os
import errno
import threading
import time
import logging

from cpy2py.kernel import state
from cpy2py.twinterpreter import bootstrap
from cpy2py.ipyc import fifo_pipe

from .main_module import TwinMainModule
from . import exceptions
from .interpreter import Interpreter
from ._kernel import TwinKernelMaster


class TwinMaster(object):
    """
    Manager for a twinterpeter

    Spawns, configures and supervises the actual interpeter process. In order to
    use any twinterpeters, a corresponding TwinMaster must be created and its
    :py:meth:`TwinMaster.start` method called.

    :param executable: path to executable of secondary interpreter
    :type executable: str or None
    :param twinterpreter_id: identified for the twinterpreter
    :type twinterpreter_id: str or None
    :param kernel: the type of kernel to use to connect interpreters
    :param ipyc: the type of interprocess communication to use
    """
    _initialized = False

    #: singleton store `twinterpreter_id` => `master`
    _master_store = {}
    _store_mutex = threading.Lock()

    def __init__(
            self, executable=None, twinterpreter_id=None, kernel=None, main_module=True, run_main=None,
            restore_argv=False, ipyc=fifo_pipe.DuplexFifoIPyC
    ):
        # avoid duplicate initialisation of singleton
        with self._store_mutex:
            self._interpreter = Interpreter(executable or twinterpreter_id)
            self.twinterpreter_id = twinterpreter_id or os.path.basename(self._interpreter.executable)
            if twinterpreter_id in self._master_store:
                raise RuntimeError('Attempt to overwrite existing Master for %r' % twinterpreter_id)
            self._master_store[self.twinterpreter_id] = self
            self.main_def = TwinMainModule(main_module, run_main, restore_argv)
            self._logger = logging.getLogger(
                '__cpy2py__.twin.%s_to_%s.master' % (state.TWIN_ID, self.twinterpreter_id)
            )
            self._process = None
            self._kernel_master = TwinKernelMaster(twin_id=self.twinterpreter_id, kernel=kernel, ipyc=ipyc, protocol=self._interpreter.pickle_protocol)

    @property
    def native(self):
        """Whether the master defines its own controlling scope"""
        return state.is_twinterpreter(self.twinterpreter_id)

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
        assert self._process is None and not self._kernel_master.alive,\
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
            self._logger.warning('<%s> Starting Twin [%s]', state.TWIN_ID, self.twinterpreter_id)
            self._process = self._interpreter.spawn(
                arguments=self._twin_args(),
                environment=self._twin_env()
            )
            time.sleep(0.1)  # sleep while child initializes
            if self._process.poll() is not None:
                raise exceptions.TwinterpreterProcessError(
                    'Twinterpreter process failed at start with %s' % self._process.poll()
                )
            self._kernel_master.accept()
            # finalize the twinterpreter
            state.TWIN_GROUP_STATE.run_finalizers(self.twinterpreter_id)
            self._logger.info('<%s> Initialized Twin [%s]', state.TWIN_ID, self.twinterpreter_id)
        else:
            self._logger.warning('<%s> Reusing Twin [%s]', state.TWIN_ID, self.twinterpreter_id)
        return self.is_alive

    def _twin_args(self):
        """Create the twin's CLI args"""
        twin_args = []
        # preserve -O
        if not __debug__:
            twin_args.append('-O')
        # bootstrap
        twin_args.extend((
                '-m', 'cpy2py.twinterpreter.bootstrap',
                '--peer-id', state.TWIN_ID,
                '--twin-id', self.twinterpreter_id,
                '--master-id', state.MASTER_ID,
                '--main-def', bootstrap.dump_main_def(self.main_def),
                '--cwd', os.getcwd(),
                ))
        twin_args.extend(self._kernel_master.cli_args)
        twin_args.append('--initializer')
        twin_args.extend(bootstrap.dump_initializer(state.TWIN_GROUP_STATE.initializers))
        return twin_args

    def _twin_env(self):
        """Create the twin's starting environment"""
        twin_env = os.environ.copy()
        twin_env['__CPY2PY_TWIN_ID__'] = self.twinterpreter_id
        twin_env['__CPY2PY_MASTER_ID__'] = state.MASTER_ID
        return twin_env

    def stop(self):
        """Terminate the twinterpreter"""
        self._cleanup()
        return self.is_alive

    def destroy(self):
        """Stop any twinterpreter and cleanup the master"""
        self.stop()
        del self._master_store[self.twinterpreter_id]
        self._logger.info('<%s> Destroyed Twin [%s]', state.TWIN_ID, self.twinterpreter_id)

    def _cleanup(self):
        """Try and close all connections"""
        self._kernel_master.shutdown()
        if self._process is not None:
            # allow twin to shut down before killing it outright
            shutdown_time = time.time()
            while self._process.poll() is None:
                time.sleep(0.1)
                if time.time() - shutdown_time > 5:
                    self._process.kill()
            if self._process.poll() is not None:
                self._process = None
                self._logger.info('<%s> Cleaned up Twin Process [%s]', state.TWIN_ID, self.twinterpreter_id)

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
        return self._kernel_master.client.request_dispatcher.dispatch_call(call, *call_args, **call_kwargs)
