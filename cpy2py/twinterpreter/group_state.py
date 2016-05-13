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
from __future__ import print_function
from cpy2py.proxy.proxy_object import TwinObject, localmethod
from cpy2py.kernel import kernel_state
import threading


class TwinInitDirective(object):
    """
    Directive for initializing twinterpreters
    """
    def __init__(self, call, args, kwargs, parent_twin_id):
        self.call = call
        self.args = args
        self.kwargs = kwargs
        self.parent_twin_id = parent_twin_id

    def __call__(self):
        self.call(*self.args, **self.kwargs)


class TwinGroupState(TwinObject):
    """
    Shared state of all twinterpreters

    A single instance of this class is registered in the :py:mod:`cpy2py`
    namespace as ``cpy2py.kernel_state.TWIN_GROUP_STATE``. It is available
    in any twinterpreter as soon as the kernel has booted.

    The group state serves as a pseudo *global module*, like :py:mod:`sys`.
    Its main purpose is to provide means to :py:meth:`~.add_initializer`
    and :py:meth:`~.add_finalizer` functions. These are run before and
    after the kernel has booted, respectively.

    :note: If you need an exit function, use :py:mod:`atexit` from a finalizer.

    :note: Both initializer and finalizer functions are never run in the
           twinterpreter defining them. You must do so explicitly.
    """
    def __init__(self):
        self._global_lock = threading.RLock()
        self.initializers = []
        self.finalizers = []

    @localmethod
    def add_initializer(self, func, *args, **kwargs):
        """
        Register a function to be run before a twinterpreter kernel starts

        :param func: function to execute
        :param args: positional arguments to ``func``
        :param kwargs: keyword arguments to ``func``
        :param init_existing: run initializer in already existing kernels; keyword only
        :type init_existing: bool
        """
        init_existing = kwargs.pop("init_existing", True)
        initializer = TwinInitDirective(call=func, args=args, kwargs=kwargs, parent_twin_id=kernel_state.TWIN_ID)
        self._add_initializer(initializer=initializer, init_existing=init_existing, collection='initializers')

    @localmethod
    def add_finalizer(self, func, *args, **kwargs):
        """
        Register a function to be run after a twinterpreter kernel starts

        :param func: function to execute
        :param args: positional arguments to ``func``
        :param kwargs: keyword arguments to ``func``
        :param init_existing: run initializer in already existing kernels; keyword only
        :type init_existing: bool
        """
        init_existing = kwargs.pop("init_existing", True)
        initializer = TwinInitDirective(call=func, args=args, kwargs=kwargs, parent_twin_id=kernel_state.TWIN_ID)
        self._add_initializer(initializer=initializer, init_existing=init_existing, collection='finalizers')

    def _add_initializer(self, initializer, init_existing, collection):
        with self._global_lock:
            getattr(self, collection).append(initializer)
            if init_existing:
                for twin_id, client in kernel_state.KERNEL_INTERFACE.items():
                    if twin_id == initializer.parent_twin_id:
                        continue
                    client.dispatch_call(initializer.call, *initializer.args, **initializer.kwargs)

    def run_finalizers(self, twin_id):
        """
        Run all finalizers in a twinterpreter

        :param twin_id:

        :note: This function is called automatically when bootstrapping
               a twinterpreter. It is not intended for manual use.
        """
        client = kernel_state.get_kernel(twin_id)
        for finalizer in self.finalizers:
            client.dispatch_call(finalizer)
