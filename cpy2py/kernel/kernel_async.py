"""
Asynchronous Kernel Client and Server

Threaded kernel that does not internally block. This kernel can serve multiple
requests at the same time, allowing for recursion across twinterpreters. Note
that this comes at the cost of starting a new thread per request.
"""
from __future__ import print_function
import threading

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
            self._logger.warning('Listening [%s]', kernel_state.TWIN_ID)
            request_id, directive = self._server_recv()
            if self._except_callback is not None:
                raise self._except_callback
            thread = threading.Thread(target=self._request_thread_main, args=(request_id, directive))
            thread.daemon = True
            thread.start()

    def _request_thread_main(self, request_id, directive):
        try:
            self.request_handler.serve_request(request_id, directive)
        except Exception as err:
            self._except_callback = err


class AsyncKernelClient(SingleThreadKernelClient):
    def __init__(self, peer_id, ipyc, pickle_protocol=2):
        SingleThreadKernelClient.__init__(self, peer_id=peer_id, ipyc=ipyc, pickle_protocol=pickle_protocol)
        self._request_send_lock = threading.Lock()
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
                request_id, reply_body = self._client_recv()
                self._requests[request_id][1] = reply_body
                self._requests[request_id][0].set()
        except (ipyc_exceptions.IPyCTerminated, EOFError):
            self._terminate.set()

    def run_request(self, request_body):
        my_id = threading.current_thread().ident
        request_done = threading.Event()
        self._requests[my_id] = [request_done, None]
        with self._request_send_lock:
            self._client_send((my_id, request_body))
        request_done.wait()
        reply_body = self._requests.pop(my_id)[1]
        return reply_body

    def stop(self):
        self._terminate.set()
        SingleThreadKernelClient.stop(self)

SERVER = AsyncKernelServer
CLIENT = AsyncKernelClient
