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
Multithreaded Kernel Client and Server

Threaded kernel that does not internally block. This kernel can serve multiple
requests at the same time, allowing for recursion across twinterpreters. A
basic form of thread-recycling is used to reduce the overhead from starting new
threads.
"""
import threading
import random

from cpy2py.utility.thread_tools import FifoQueue, ItemError, ThreadGuard
from .kernel_async import AsyncKernelClient, AsyncKernelServer


class MultiThreadKernelServer(AsyncKernelServer):
    """
    Multithreaded kernel server for sending requests to other interpreter in parallel

    :param peer_id: id of the kernel/twinterpreter this kernel is peered with
    :type peer_id: str
    :param ipyc: :py:mod:`~IPyC` for incoming requests
    :type ipyc: :py:class:`~DuplexFifoIPyC`
    :param pickle_protocol: protocol number for :py:mod:`pickle`
    :type pickle_protocol: int
    """
    def __init__(self, peer_id, ipyc, pickle_protocol=2):
        AsyncKernelServer.__init__(self, peer_id=peer_id, ipyc=ipyc, pickle_protocol=pickle_protocol)
        self._worker_threads = set()
        self._work_queue = FifoQueue()
        self._idle_workers = ThreadGuard(0)

    def _dispatch_request_handling(self, request_id, directive):
        self._work_queue.put((request_id, directive))
        if self._work_queue.qsize() > self._idle_workers:
            self._start_worker()

    def _start_worker(self):
        thread = threading.Thread(target=self._worker_thread_main)
        thread.daemon = True
        self._worker_threads.add(thread)
        thread.start()

    def _worker_thread_main(self):
        while True:
            self._idle_workers += 1
            try:
                request_id, directive = self._work_queue.get(True, 9 + 2 * random.random())
            except ItemError:
                # avoid race condition by removing us FIRST, then checking if any are left
                self._worker_threads.remove(threading.currentThread())
                if not self._worker_threads:
                    # no other thread alive, stick around
                    self._worker_threads.add(threading.currentThread())
                    continue
                else:
                    break
            finally:
                self._idle_workers -= 1
            try:
                self.request_handler.serve_request(request_id, directive)
            except Exception as err:  # pylint: disable=broad-except
                self._except_callback = err

SERVER = MultiThreadKernelServer
CLIENT = AsyncKernelClient
