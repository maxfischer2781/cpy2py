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
import subprocess

from cpy2py.utility.compat import stringabc
from cpy2py.kernel.flavours import async, threaded, single

from .interpreter import Interpreter


class TwinProcess(object):
    """
    Definition of how a twinterpreter operates

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
        'single': single,
        'async': async,
        'multi': threaded,
    }

    @property
    def executable(self):
        return self.interpreter.executable

    @property
    def pickle_protocol(self):
        return self.interpreter.pickle_protocol

    def __init__(self, executable=None, twinterpreter_id=None, kernel=None):
        # Resolve incomplete argument list using defaults
        assert executable is not None or twinterpreter_id is not None,\
            "At least one of 'executable' and 'twinterpreter_id' must be set"
        if executable is None:
            interpreter = Interpreter(twinterpreter_id)
        elif not isinstance(executable, Interpreter):
            interpreter = Interpreter(executable)
        else:
            interpreter = executable
        if twinterpreter_id is None:
            twinterpreter_id = os.path.basename(interpreter.executable)
        self.interpreter = interpreter
        self.twinterpreter_id = twinterpreter_id
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

    def spawn(self, cli_args=None, env=None):
        """
        Spawn the Twinterpreter process

        :param cli_args: command line arguments to pass to process
        :type cli_args: list[str] or None
        :param env: environment to pass to process
        :type env: dict or None
        :returns: the spawned process
        :rtype: :py:class:`subprocess.Popen`
        """
        return self.interpreter.spawn(arguments=cli_args, environment=env)

    def __repr__(self):
        return '%s(executable=%r, twinterpreter_id=%r, kernel=%r)' % (
            self.__class__.__name__,
            self.executable,
            self.twinterpreter_id,
            self.kernel
        )

    def __eq__(self, other):
        try:
            return self.executable == other.executable\
                and self.twinterpreter_id == other.twinterpreter_id\
                and self.kernel == other.kernel
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        return not self == other