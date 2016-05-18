import os

from cpy2py.utility import proc_tools
from cpy2py.kernel import kernel_single, kernel_async, kernel_multi


class TwinDef(object):
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