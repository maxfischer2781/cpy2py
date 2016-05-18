from __future__ import print_function
import os
import atexit
import socket
import logging
import collections
import tempfile
import errno

from cpy2py.utility.compat import BytesFile, inf
from cpy2py.utility.utils import random_str
from cpy2py.kernel import kernel_state


class DuplexSocketIPyC(object):
    def __init__(self, family=socket.AF_UNIX, address=None, is_master=True):
        self.is_master = is_master
        self.family = family
        if self.is_master:
            self.server_socket = self._create_server_socket(family=family, address=address)
            self.address = self.server_socket.getsockname()
        else:
            self.server_socket = None
            self.address = address
        self.client_socket = None
        self._logger = logging.getLogger('__cpy2py__.ipyc.%s' % self.__class__.__name__)
        self._buffer = collections.deque()

    @staticmethod
    def _create_server_socket(family, address):
        sock = socket.socket(family=family)
        if address is not None:
            sock.bind(address)
        else:
            # choose a random address
            if family == socket.AF_UNIX:
                socket_name = tempfile.mktemp()
                socket_name += random_str(96 - len(socket_name))  # AF_UNIX allows for 108 chars, minus padding
                atexit.register(os.remove, socket_name)
                sock.bind(socket_name)
            else:
                sock.bind((socket.getfqdn(), 0))  # port 0: let OS pick as appropriate
        sock.listen(1)
        return sock

    def open(self):
        """Open connections"""
        if self.is_master:
            self.client_socket, client_address = self.server_socket.accept()
            self._logger.warning(
                '<%s> [%s] accepted from %r',
                kernel_state.TWIN_ID,
                self.__class__.__name__,
                client_address
            )
        else:
            self.client_socket = socket.socket(family=self.family)
            self.client_socket.connect(self.address)
            self._logger.warning(
                '<%s> [%s] connected from %r',
                kernel_state.TWIN_ID,
                self.__class__.__name__,
                self.client_socket.getsockname()
            )

    def close(self):
        """Close connections"""
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
        except socket.error as err:
            if err.errno not in (errno.ENOTCONN, errno.EBADF):
                raise
        self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()

    # file interface
    def read(self, size=None):
        """Read at most `size` bytes"""
        if size is None:
            raise NotImplementedError
        else:
            return self.client_socket.recv(size)

    def readline(self):
        """Read one entire line"""
        raise NotImplementedError

    def write(self, message):
        """Write a string"""
        return self.client_socket.send(message)

    # socket doesn't have lightweight file interface, use our own wrappers
    @property
    def writer(self):
        return BufferedSocketFile(self.client_socket)

    @property
    def reader(self):
        return BufferedSocketFile(self.client_socket)

    @property
    def connector(self):
        """Pickle'able connector as (factory, args, kwargs)"""
        # socket.AF_* is enum in Py3
        return self.__class__, (), {'family': int(self.family), 'address': self.address, 'is_master': False}

    def __repr__(self):
        return '%s(family=%r, address=%r, is_master=%s)' % (self.__class__.__name__, self.family, self.address, self.is_master)


class BufferedSocketFile(object):
    """
    File-like interface to a socket, buffered for use with :py:mod:`pickle`
    """
    #
    def __init__(self, client_socket):
        self.client_socket = client_socket
        self._read_buffer = None
        self._read_buffer_left = 0

    def read(self, size=None):
        #print('read %s' % size)
        if self._read_buffer_left <= 0:
            self._read_message()
        if size is None or size <= 0:
            self._read_buffer_left = 0
        else:
            self._read_buffer_left -= size
        return self._read_buffer.read(size)

    def readline(self):
        """Read an entire line"""
        if self._read_buffer_left <= 0:
            self._read_message()
        msg = self._read_buffer.readline()
        self._read_buffer_left -= len(msg)
        return msg

    def _read_message(self):
        """
        Read one message from the socket
        """
        try:
            msg_len = b''
            while len(msg_len) < 8:
                msg_len += self.client_socket.recv(8 - len(msg_len))
            #print(msg_len)
            msg_len = int(msg_len, 16)
            msg_read = 0
            msg_buffer = []
            while msg_read < msg_len:
                msg_buffer.append(self.client_socket.recv(min(msg_len - msg_read, 4096)))
                msg_read += len(msg_buffer[-1])
            self._read_buffer = BytesFile(b''.join(msg_buffer))
            self._read_buffer_left = len(self._read_buffer.getvalue())
        except socket.error as err:
            if err.errno == errno.EBADF:
                raise EOFError
            raise

    def _write_message(self, message):
        #print('write %d' % len(message))
        self.client_socket.sendall(('%08X' % len(message)).encode('ascii'))
        self.client_socket.sendall(message)

    write = _write_message
