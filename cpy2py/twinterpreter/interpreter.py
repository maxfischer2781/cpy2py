from __future__ import print_function
import platform
import pickle
import sys
import json
import textwrap
import subprocess

from ..utility.compat import check_output
from ..utility.twinspect import exepath

from .exceptions import RemoteCpy2PyNotFound


_IPC_ENCODING = 'utf-8'


def print_metadata():
    """Write metadata about **the current** interpreter to stdout"""
    data = {
        'python_implementation': platform.python_implementation(),
        'python_version_info': tuple(sys.version_info),
        'pickle_protocol': pickle.HIGHEST_PROTOCOL,
    }
    if sys.version_info < (3,):
        out_stream = sys.stdout
    else:
        out_stream = sys.stdout.buffer
    out_stream.write(json.dumps(data).encode(_IPC_ENCODING) + b'\n')


class Interpreter(object):
    """
    Representation of a Python interpreter

    :param executable: executable launching the interpreter
    :type executable: str

    This class provides metadata about the capabilities of ``executable``.
    The remote environment is validated during this -
    any instance can initialise a twinterpreter using :py:meth:`~.Interpreter.spawn`.
    """
    @property
    def pickle_protocol(self):
        """The highest :py:mod:`pickle` protocol available for mutual communication"""
        return min(pickle.HIGHEST_PROTOCOL, self._pickle_protocol)

    def __init__(self, executable):
        self.executable = exepath(executable)
        #: the result of ``sys.version_info`` as a tuple
        self.python_version_info = None
        #: the implementation, such as ``"CPython"`` or ``"PyPy"``
        self.python_implementation = None
        self._pickle_protocol = None
        self._get_metadata()

    def _get_metadata(self):
        raw_data = check_output(  # type: bytes
            [
                self.executable, '-c', textwrap.dedent("""\
                try:
                    from cpy2py.twinterpreter.interpreter import print_metadata
                except ImportError:
                    print('null')
                else:
                    print_metadata()
                """)
            ])
        meta_data = json.loads(raw_data.decode(_IPC_ENCODING))
        if meta_data is None:
            raise RemoteCpy2PyNotFound(self.executable)
        self.python_version_info = tuple(meta_data['python_version_info'])
        self.python_implementation = meta_data['python_implementation']
        self._pickle_protocol = meta_data['pickle_protocol']

    def __eq__(self, other):
        if isinstance(other, Interpreter):
            return self.executable == other.executable

    def __repr__(self):
        return '<Twinterpreter %r (%s %s)>' % (
            self.executable, self.python_implementation, '.'.join(str(field) for field in self.python_version_info)
        )

    def spawn(self, arguments=None, environment=None):
        """
        Spawn a new instance of this interpreter

        :param arguments: command line arguments to pass to the interpreter
        :type arguments: list[str] or None
        :param environment: environment in which to run the interpreter
        :type environment: dict or None
        :returns: the spawned process
        :rtype: :py:class:`subprocess.Popen`

        :note: This does not spawn a twinterpreter by itself.
               Supply the appropriate arguments and environment as required.
        """
        return subprocess.Popen(
            args=[self.executable] + ([] or arguments),
            # do not redirect std streams
            # this fakes the impression of having just one program running
            stdin=None,
            stdout=None,
            stderr=None,
            env=environment,
        )
