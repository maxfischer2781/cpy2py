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
Asynchronous Kernel Client and Server

Threaded kernel that does not internally block. This kernel can serve multiple
requests at the same time, allowing for recursion across twinterpreters. Note
that this comes at the cost of starting a new thread per request.
"""
from __future__ import print_function
import threading

from cpy2py.utility.exceptions import format_exception
from cpy2py.ipyc import ipyc_exceptions
from cpy2py.kernel import kernel_state
from cpy2py.kernel.kernel_single import SingleThreadKernelClient, SingleThreadKernelServer


class AsyncKernelServer(SingleThreadKernelServer):
    """
    Anychronous kernel server for sending requests to other interpreter in parallel

    :param peer_id: id of the kernel/twinterpreter this kernel is peered with
    :type peer_id: str
    :param ipyc: :py:mod:`~IPyC` for incoming requests
    :type ipyc: :py:class:`~DuplexFifoIPyC`
    :param pickle_protocol: protocol number for :py:mod:`pickle`
    :type pickle_protocol: int
    """
    def __init__(self, peer_id, ipyc, pickle_protocol=2):
        SingleThreadKernelServer.__init__(self, peer_id=peer_id, ipyc=ipyc, pickle_protocol=pickle_protocol)
        self._except_callback = None

    def _serve_requests(self):
        while not self._terminate.is_set():
            if __debug__:
                self._logger.warning('<%s> [%s] Server Listening', kernel_state.TWIN_ID, self.peer_id)
            request_id, directive = self._server_recv()
            if self._except_callback is not None:
                raise self._except_callback  # pylint: disable=raising-bad-type
            self._dispatch_request_handling(request_id, directive)

    def _dispatch_request_handling(self, request_id, directive):
        thread = threading.Thread(target=self._request_thread_main, args=(request_id, directive))
        thread.daemon = True
        thread.start()

    def _request_thread_main(self, request_id, directive):
        try:
            self.request_handler.serve_request(request_id, directive)
        except Exception as err:  # pylint: disable=broad-except
            self._except_callback = err


class AsyncKernelClient(SingleThreadKernelClient):
    def __init__(self, peer_id, ipyc, pickle_protocol=2):
        SingleThreadKernelClient.__init__(self, peer_id=peer_id, ipyc=ipyc, pickle_protocol=pickle_protocol)
        self._request_send_lock = threading.RLock()
        # request_id => (signal, reply)
        self._requests = {}
        self._terminate = threading.Event()
        self._terminate.set()
        self._thread = threading.Thread(target=self._digest_replies)
        self._thread.daemon = True
        self._thread.start()

    def _digest_replies(self):
        self._terminate.clear()
        try:
            while not self._terminate.is_set():
                if __debug__:
                    self._logger.warning('<%s> [%s] Client Listening', kernel_state.TWIN_ID, self.peer_id)
                request_id, reply_body = self._client_recv()
                request = self._requests.pop(request_id)
                request[1] = reply_body
                request[0].set()
                del request_id, reply_body, request
        except (ipyc_exceptions.IPyCTerminated, EOFError, ValueError):
            self._logger.warning('<%s> [%s] Client Released', kernel_state.TWIN_ID, self.peer_id)
            self.stop_local()
        except Exception as err:  # pylint: disable=broad-except
            if isinstance(err, KeyError):
                self._logger.critical('Request: %r (%s)', request_id, type(request_id))
                for key in self._requests:
                    self._logger.critical('Await  : %r (%s)', key, type(key))
            self._logger.critical(
                '<%s> [%s] TWIN KERNEL INTERNAL EXCEPTION: %s', kernel_state.TWIN_ID, self.peer_id, err
            )
            format_exception(self._logger, 3)
            raise

    def run_request(self, request_body):
        my_id = threading.current_thread().ident
        with self._request_send_lock:
            self._requests[my_id] = my_request = [threading.Event(), self.request_dispatcher.empty_reply]
            self._client_send((my_id, request_body))
        my_request[0].wait()
        return my_request[1]

    def run_event(self, event_body):
        with self._request_send_lock:
            self._client_send((None, event_body))

    def stop(self):
        with self._request_send_lock:
            self._terminate.set()
            return SingleThreadKernelClient.stop(self)

    def stop_local(self):
        """Shutdown the local server"""
        self._release_requests()
        SingleThreadKernelClient.stop_local(self)

    def _release_requests(self):
        """Release all outstanding requests"""
        with self._request_send_lock:
            self._terminate.set()
            while True:
                try:
                    self._requests.popitem()[1][0].set()
                except KeyError:
                    break


SERVER = AsyncKernelServer
CLIENT = AsyncKernelClient
