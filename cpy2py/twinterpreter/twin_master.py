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
import cpy2py.twinterpreter.kernel_state

import cpy2py.twinterpreter.kernel
import cpy2py.twinterpreter.bootstrap
import cpy2py.ipyc.stdstream
from cpy2py import proxy


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

    :note: Only one kernel may use a specific `twinterpreter_id` at any time.
    """
    executable = None
    twinterpreter_id = None

    def __init__(self, executable=None, twinterpreter_id=None):
        self.executable = executable or self.__class__.executable
        self.twinterpreter_id = twinterpreter_id or self.__class__.twinterpreter_id or self.executable
        self._process = None
        self._kernel = None

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
            else:
                return True
        return False

    def start(self):
        """
        Start the twinterpeter if it is not alive

        :returns: whether the twinterpeter is alive
        """
        if not self.is_alive:
            self._process = subprocess.Popen(
                [
                    self.executable, '-m', cpy2py.twinterpreter.bootstrap.__name__,
                    '--peer-id', cpy2py.twinterpreter.kernel_state.__twin_id__,
                    '--twin-id', self.twinterpreter_id,
                    '--master-id', cpy2py.twinterpreter.kernel_state.__master_id__,
                    '--twin-group-id',
                    cpy2py.twinterpreter.kernel_state.__twin_group_id__,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            self._kernel = cpy2py.twinterpreter.kernel.SingleThreadKernel(
                self.twinterpreter_id,
                ipc=cpy2py.ipyc.stdstream.StdIPC(
                    readstream=self._process.stdout,
                    writestream=self._process.stdin,
                    pickler_cls=proxy.twin_pickler,
                    unpickler_cls=proxy.twin_unpickler,
                )
            )
        return self.is_alive

    def stop(self):
        """Terminate the twinterpreter"""
        if self._kernel is not None:
            self._kernel.stop()
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


class TwinPyPy(TwinMaster):
    """
    PyPy twinterpreter
    """
    executable = 'pypy'
    twinterpreter_id = 'pypy'
