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
import ast
import operator

from .compat import stringabc, inf, intern_str, unicode_str, long_int
from .exceptions import CPy2PyException


#: sentinel for unset variables
UNSET = intern_str("<unset_sentinel>")


class ThreadGuard(object):
    """
    Threadsafe wrapper for primitives

    This class wraps all magic methods (e.g. ``a + b``, ``a[b]``) to
    make them atomic.

    :note: Derived values inherit the original type. For example,
           ``foo = ThreadGuard(1.0) * 2`` will be of type
           :py:class:`float`, i.e. the result of ``1.0 * 2``.

    :note: When invoked as a context manager, the underlying lock
           will be held until the context is exited.
    """
    def __init__(self, start=0.0, lock_type=Lock):
        if isinstance(start, stringabc):
            start = ast.literal_eval(start)
        self._value = start
        self._lock = lock_type()

    # Developer note:
    # operations are implemented using operator.__add__(self._value, other)
    # instead of self._value.__add__(other) as the later does *not* imply
    # calling other.__radd__(self._value) on failure.
    def __add__(self, other):
        with self._lock:
            return operator.__add__(self._value, other)

    def __sub__(self, other):
        with self._lock:
            return operator.__sub__(self._value, other)

    def __mul__(self, other):
        with self._lock:
            return operator.__mul__(self._value, other)

    # __div__ is py2 only
    if hasattr(operator, '__div__'):
        def __div__(self, other):
            with self._lock:
                return operator.__div__(self._value, other)

    def __truediv__(self, other):
        with self._lock:
            return operator.__truediv__(self._value, other)

    def __floordiv__(self, other):
        with self._lock:
            return operator.__floordiv__(self._value, other)

    def __mod__(self, other):
        with self._lock:
            return operator.__mod__(self._value, other)

    def __divmod__(self, other):
        with self._lock:
            return divmod(self._value, other)

    def __pow__(self, power, modulo=None):
        with self._lock:
            return pow(self._value, power, modulo)

    def __lshift__(self, other):
        with self._lock:
            return operator.__lshift__(self._value, other)

    def __rshift__(self, other):
        with self._lock:
            return operator.__rshift__(self._value, other)

    def __and__(self, other):
        with self._lock:
            return operator.__and__(self._value, other)

    def __xor__(self, other):
        with self._lock:
            return operator.__xor__(self._value, other)

    def __or__(self, other):
        with self._lock:
            return operator.__or__(self._value, other)

    def __radd__(self, other):
        with self._lock:
            return operator.__add__(other, self._value)

    def __rsub__(self, other):
        with self._lock:
            return operator.__sub__(other, self._value)

    def __rmul__(self, other):
        with self._lock:
            return operator.__mul__(other, self._value)

    if hasattr(operator, '__div__'):
        def __rdiv__(self, other):
            with self._lock:
                return operator.__div__(other, self._value)

    def __rtruediv__(self, other):
        with self._lock:
            return operator.__truediv__(other, self._value)

    def __rfloordiv__(self, other):
        with self._lock:
            return operator.__floordiv__(other, self._value)

    def __rmod__(self, other):
        with self._lock:
            return operator.__mod__(other, self._value)

    def __rdivmod__(self, other):
        with self._lock:
            return divmod(other, self._value)

    def __rpow__(self, other):
        with self._lock:
            return operator.__pow__(other, self._value)

    def __rlshift__(self, other):
        with self._lock:
            return operator.__lshift__(other, self._value)

    def __rrshift__(self, other):
        with self._lock:
            return operator.__rshift__(other, self._value)

    def __rand__(self, other):
        with self._lock:
            return operator.__and__(other, self._value)

    def __rxor__(self, other):
        with self._lock:
            return operator.__xor__(other, self._value)

    def __ror__(self, other):
        with self._lock:
            return operator.__or__(other, self._value)

    # inplace operations
    def __iadd__(self, other):
        with self._lock:
            self._value += other
            return self

    def __isub__(self, other):
        with self._lock:
            self._value -= other
            return self

    def __imul__(self, other):
        with self._lock:
            self._value *= other
            return self

    if hasattr(operator, '__idiv__'):
        def __idiv__(self, other):
            with self._lock:
                self._value = operator.__idiv__(self._value, other)
                return self

    def __itruediv__(self, other):
        with self._lock:
            self._value = operator.__itruediv__(self._value, other)
            return self

    def __ifloordiv__(self, other):
        with self._lock:
            self._value //= other
            return self

    def __imod__(self, other):
        with self._lock:
            self._value %= other
            return self

    def __ipow__(self, power, modulo=None):
        with self._lock:
            self._value = pow(self._value, power, modulo)
            return self

    def __ilshift__(self, other):
        with self._lock:
            self._value <<= other
            return self

    def __irshift__(self, other):
        with self._lock:
            self._value >>= other
            return self

    def __iand__(self, other):
        with self._lock:
            self._value &= other
            return self

    def __ixor__(self, other):
        with self._lock:
            self._value ^= other
            return self

    def __ior__(self, other):
        with self._lock:
            self._value |= other
            return self

    def __neg__(self):
        with self._lock:
            return -self._value

    def __pos__(self):
        with self._lock:
            return +self._value

    def __abs__(self):
        with self._lock:
            return abs(self._value)

    def __invert__(self):
        with self._lock:
            return ~self._value

    def __complex__(self):
        with self._lock:
            return complex(self._value)

    def __int__(self):
        with self._lock:
            return int(self._value)

    def __float__(self):
        with self._lock:
            return float(self._value)

    def __long__(self):
        with self._lock:
            return long_int(self._value)

    def __round__(self):
        with self._lock:
            return round(self._value)

    def __index__(self):
        try:
            with self._lock:
                return self._value.__index__()
        except AttributeError:
            return NotImplemented

    def __enter__(self):
        self._lock.acquire()
        try:
            _enter = self._value.__enter__
        except AttributeError:
            self._lock.release()
        else:
            return _enter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            _exit = self._value.__exit__
            return _exit(exc_type, exc_val, exc_tb)
        finally:
            self._lock.release()

    def __str__(self):
        with self._lock:
            return str(self._value)

    def __unicode__(self):
        with self._lock:
            return unicode_str(self._value)

    def __repr__(self):
        with self._lock:
            return '%s<%r>' % (self.__class__.__name__, self._value)

    def __bytes__(self):
        with self._lock:
            return bytes(self._value)

    def __lt__(self, other):
        with self._lock:
            return self._value < other

    def __gt__(self, other):
        with self._lock:
            return self._value > other

    def __le__(self, other):
        with self._lock:
            return self._value <= other

    def __ge__(self, other):
        with self._lock:
            return self._value >= other

    def __eq__(self, other):
        with self._lock:
            return self._value == other

    def __ne__(self, other):
        with self._lock:
            return self._value != other

    def __hash__(self):
        with self._lock:
            return hash(self._value)

    def __nonzero__(self):
        with self._lock:
            return bool(self._value)

    __bool__ = __nonzero__

    def __call__(self, *args, **kwargs):
        with self._lock:
            return self._value(*args, **kwargs)


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
                with wait_mutex:
                    with self._queue_mutex:
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
                                try:
                                    return self._queue_content.pop()
                                except IndexError:  # someone else beat us to it, continue waiting
                                    pass
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






