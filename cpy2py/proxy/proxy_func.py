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
from cpy2py.utility.proxy import clone_function_meta
from cpy2py.kernel import kernel_state


def twinfunction(twinterpreter_id):
    """
    Decorator to make a function native to a twinterpreter

    :param twinterpreter_id: identifier for the twin which executes the function
    :type twinterpreter_id: str

    :note: The resulting proxy object does only pass on function calls. Other
           operations, e.g. attribute assignment, only modify the proxy.
    """
    def decorator(func):
        func.__twin_id__ = twinterpreter_id
        # native twin, never redirect
        if kernel_state.is_twinterpreter(twinterpreter_id):
            return func
        # redirect to kernel
        # - must dispatch to the proxy, otherwise pickling will fail
        # - lazily select the kernel on first call to allow late-binding
        # -- the funtion is proxied by the function_dispatch_proxy
        # -- on the first call, function_runner_factory fetches the kernel
        # -- on subsequent calls, function_runner is used directly

        def function_runner_factory(*fargs, **fkwargs):
            def function_runner(*args, **kwargs):
                return function_runner.dispatch_call(function_dispatch_proxy, *args, **kwargs)
            function_runner.dispatch_call = kernel_state.get_kernel(twinterpreter_id).dispatch_call
            function_dispatch_proxy.function_runner = function_runner
            return function_runner(*fargs, **fkwargs)

        def function_dispatch_proxy(*args, **kwargs):
            return function_dispatch_proxy.function_runner(*args, **kwargs)
        function_dispatch_proxy.function_runner = function_runner_factory

        clone_function_meta(func, function_dispatch_proxy)
        return function_dispatch_proxy
    return decorator
