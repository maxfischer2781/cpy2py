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
"""
The kernel is the main thread of execution running inside a twinterpreter.

Any connection between twinterpreters is handled by two kernels. Each
consists of client and server side residing in the different interpreters.

The kernels assume that they have been setup properly. Use
:py:class:`~cpy2py.twinterpreter.twin_master.TwinMaster` start kernel pairs.
"""
import sys
import os
import time
import logging
import threading

from cpy2py.utility.compat import pickle
from cpy2py.kernel import kernel_state

from cpy2py.utility.exceptions import format_exception, CPy2PyException
from cpy2py.ipyc import ipyc_exceptions
from cpy2py.kernel.kernel_exceptions import TwinterpeterTerminated, StopTwinterpreter
from cpy2py.proxy import proxy_tracker
from cpy2py.kernel.kernel_requesthandler import RequestDispatcher, RequestHandler

# Message Enums
# twin call type
__E_SHUTDOWN__ = -1
__E_CALL_FUNC__ = 11
__E_CALL_METHOD__ = 12
__E_GET_ATTRIBUTE__ = 21
__E_SET_ATTRIBUTE__ = 22
__E_DEL_ATTRIBUTE__ = 23
__E_INSTANTIATE__ = 31
__E_REF_INCR__ = 32
__E_REF_DECR__ = 33
# twin reply type
__E_SUCCESS__ = 101
__E_EXCEPTION__ = 102

E_SYMBOL = {
    __E_SHUTDOWN__: '__E_SHUTDOWN__',
    __E_CALL_FUNC__: '__E_CALL_FUNC__',
    __E_CALL_METHOD__: '__E_CALL_METHOD__',
    __E_GET_ATTRIBUTE__: '__E_GET_ATTRIBUTE__',
    __E_SET_ATTRIBUTE__: '__E_SET_ATTRIBUTE__',
    __E_DEL_ATTRIBUTE__: '__E_DEL_ATTRIBUTE__',
    __E_INSTANTIATE__: '__E_INSTANTIATE__',
    __E_REF_INCR__: '__E_REF_INCR__',
    __E_REF_DECR__: '__E_REF_DECR__',
    __E_SUCCESS__: '__E_SUCCESS__',
    __E_EXCEPTION__: '__E_EXCEPTION__',
}


def _connect_ipyc(ipyc, pickle_protocol):
    """Connect pickle/unpickle trackers to a duplex IPyC"""
    pickler = pickle.Pickler(ipyc.writer, pickle_protocol)
    pickler.persistent_id = proxy_tracker.persistent_twin_id
    send = pickler.dump
    unpickler = pickle.Unpickler(ipyc.reader)
    unpickler.persistent_load = proxy_tracker.persistent_twin_load
    recv = unpickler.load
    return send, recv


class SingleThreadKernelServer(object):
    """
    Default kernel server for sending requests to other interpreter

    :param peer_id: id of the kernel/twinterpreter this kernel is peered with
    :type peer_id: str
    :param ipyc: :py:mod:`~IPyC` for incoming requests
    :type ipyc: :py:class:`~DuplexFifoIPyC`
    :param pickle_protocol: protocol number for :py:mod:`pickle`
    :type pickle_protocol: int
    """
    def __new__(cls, peer_id, *args, **kwargs):  # pylint: disable=unused-argument
        assert peer_id not in kernel_state.KERNEL_SERVERS, 'Twinterpreters must have unique IDs'
        kernel_state.KERNEL_SERVERS[peer_id] = object.__new__(cls)
        return kernel_state.KERNEL_SERVERS[peer_id]

    def __init__(self, peer_id, ipyc, pickle_protocol=2):
        self._logger = logging.getLogger('__cpy2py__.%s' % kernel_state.TWIN_ID)
        self.peer_id = peer_id
        self._ipyc = ipyc
        self._ipyc.open()
        self._server_send, self._server_recv = _connect_ipyc(ipyc, pickle_protocol)
        self._terminate = threading.Event()
        self._terminate.set()
        self._request_handler = RequestHandler(peer_id=self.peer_id, kernel_server=self)

    def run(self):
        """
        Run the kernel request server

        :returns: exit code indicating potential failure
        """
        assert self._terminate.is_set(), 'Kernel already active'
        self._terminate.clear()
        exit_code, request_id = 1, None
        self._logger.warning('Starting kernel %s @ %s', kernel_state.TWIN_ID, time.asctime())
        try:
            while not self._terminate.is_set():
                self._logger.warning('Listening [%s]', kernel_state.TWIN_ID)
                request_id, directive = self._server_recv()
                self._request_handler.serve_request(request_id, directive)
        except StopTwinterpreter as err:
            self._server_send((request_id, __E_SHUTDOWN__, err.exit_code))
            exit_code = err.exit_code
        # cPickle may raise EOFError by itself
        except (ipyc_exceptions.IPyCTerminated, EOFError):
            exit_code = 0
        except Exception as err:  # pylint: disable=broad-except
            self._logger.critical('TWIN KERNEL INTERNAL EXCEPTION')
            format_exception(self._logger, 3)
            self._server_send((request_id, __E_EXCEPTION__, err))
        finally:
            self._terminate.set()
            self._logger.critical('TWIN KERNEL SHUTDOWN: %s => %d', kernel_state.TWIN_ID, exit_code)
            self._ipyc.close()
            del kernel_state.KERNEL_SERVERS[self.peer_id]
        return exit_code

    def send_reply(self, request_id, reply_body):
        self._server_send((request_id, reply_body))

    def stop(self):
        """Shutdown the local server"""
        # just tell server thread to stop, it'll cleanup automatically
        self._terminate.set()
        return True

    def __repr__(self):
        return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())


class SingleThreadKernelClient(object):
    """
    Default kernel client for sending requests to other interpreter

    :param peer_id: id of the kernel/twinterpreter this kernel is peered with
    :type peer_id: str
    :param ipyc: :py:mod:`~IPyC` for outgoing requests
    :type ipyc: :py:class:`~DuplexFifoIPyC`
    :param pickle_protocol: protocol number for :py:mod:`pickle`
    :type pickle_protocol: int
    """
    def __new__(cls, peer_id, *args, **kwargs):  # pylint: disable=unused-argument
        assert peer_id not in kernel_state.KERNEL_CLIENTS, 'Twinterpreters must have unique IDs'
        kernel_state.KERNEL_CLIENTS[peer_id] = object.__new__(cls)
        return kernel_state.KERNEL_CLIENTS[peer_id]

    def __init__(self, peer_id, ipyc, pickle_protocol=2):
        self._logger = logging.getLogger('__cpy2py__.%s' % kernel_state.TWIN_ID)
        self.peer_id = peer_id
        # communication
        self._ipyc = ipyc
        self._ipyc.open()
        self._client_send, self._client_recv = _connect_ipyc(ipyc, pickle_protocol)
        self._request_id = 0
        self.request_dispatcher = RequestDispatcher(peer_id=self.peer_id, kernel_client=self)
        kernel_state.KERNEL_INTERFACE[peer_id] = self.request_dispatcher

    def run_request(self, request_body):
        self._request_id += 1
        my_id = self._request_id
        self._client_send((my_id, request_body))
        request_id, reply_body = self._client_recv()
        assert request_id == my_id, 'kernel messages order'
        return reply_body

    def stop(self):
        """Shutdown the peer's server"""
        if self.request_dispatcher.shutdown_peer():
            self._ipyc.close()
            del kernel_state.KERNEL_CLIENTS[self.peer_id]
            del kernel_state.KERNEL_INTERFACE[self.peer_id]
            return True
        return False

    def __repr__(self):
        return '<%s[%s@%s]>' % (self.__class__.__name__, sys.executable, os.getpid())
