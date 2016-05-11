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
Tools for working with objects

This module re-implements several STL threading objects in a lightweight
fashion, portable across python versions.
"""
from threading import Lock
from collections import deque
import time

from .compat import inf, intern_str
from .exceptions import CPy2PyException


#: sentinel for unset variables
UNSET = intern_str("<unset_sentinel>")


class ItemError(CPy2PyException):
    """No Items in the queue"""


class FifoQueue(object):
    """
    Lighweight FIFO Queue

    This is essentially a thread-safe :py:class:`~collections.deque`.

    The additional tuning parameters :py:attr:`~sleep_min`, :py:attr:`~sleep_max`,
    :py:attr:`~sleep_fail_penalty` and :py:attr:`~sleep_order_penalty` only apply
    if python does not support the ``timeout`` argument to
    :py:meth:`threading.Lock.acquire`.
    """
    #: minimum interval between polling for new elements
    sleep_min = 0.00005
    #: maximum interval between polling for new elements
    sleep_max = 0.001
    #: factor applied to interval after unsuccessful poll
    sleep_fail_penalty = 1.5
    #: factor applied to interval for every preceeding request
    sleep_order_penalty = 2

    def __init__(self):
        self._queue_content = deque()
        self._queue_mutex = Lock()
        self._waiters = []

    def __len__(self):
        return len(self._queue_content)

    def __nonzero__(self):
        return bool(self._queue_content)

    def qsize(self):
        """Size of the queue, alias for ``len(this)``"""
        return len(self)

    def put(self, item):
        """Put a single item in the queue"""
        with self._queue_mutex:
            self._queue_content.append(item)
            if self._waiters:
                self._waiters[0].release()

    def get(self, block=True, timeout=inf):
        """
        Retrieve a single item from the queue

        :param block: whether to wait for an item if the queue is currently empty
        :type block: bool
        :param timeout: how long to wait for an item
        :type timeout: int or float
        :return: an item from the queue
        :raises: :py:exc:`~.ItemError` if no item could be retrieved
        """
        with self._queue_mutex:
            try:
                # always try if anything is ready
                return self._queue_content.pop()
            except IndexError:
                if not block:
                    raise ItemError
                # register ourselves as waiting for content
                wait_mutex = Lock()
                wait_mutex.acquire()  # lock mutex so we can wait for its release
                self._waiters.append(wait_mutex)
        try:
            if not timeout or timeout <= 0 or timeout == inf:
                with wait_mutex, self._queue_mutex:
                    return self._queue_content.pop()
            else:
                # in Py3, we can explicitly block for a specific time
                try:
                    if wait_mutex.acquire(True, timeout):
                        with self._queue_mutex:
                            return self._queue_content.pop()
                    else:
                        raise ItemError
                except TypeError:
                    # Replicate the diminishing wait behaviour of threading.Condition
                    _w_min, _w_max, _w_fail, _w_order = (
                        self.sleep_min, self.sleep_max, self.sleep_fail_penalty, self.sleep_order_penalty)
                    _w_start, _w_now, _w_idx, _w_cnt = time.time(), _w_min / _w_fail, self._waiters.index(wait_mutex), 1
                    while True:
                        with self._queue_mutex:
                            if wait_mutex.acquire(False):
                                return self._queue_content.pop()
                        _w_now = min(
                            _w_now * _w_fail * (_w_order ** _w_idx),  # diminishing wake
                            _w_start + timeout - time.time(),  # timeout
                            _w_max  # minimum responsiveness
                        )
                        if _w_now < 0:
                            raise ItemError
                        time.sleep(_w_now)
                        _w_cnt += 1
        finally:
            # always clean up
            self._waiters.remove(wait_mutex)






