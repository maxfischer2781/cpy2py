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
State of this twinterpreter

:note: This module is auto-initialized as part of the :py:mod:`cpy2py` import.
       Slaved twinterpreters are initialized via
       :py:func:`~cpy2py.twinterpreter.bootstrap.bootstrap_kernel` on startup.

:note: The only attribute feasible to set manually is :py:data:`~.master_id`.
       This must be done before any slaves are started.
"""
import os
import sys

from cpy2py.twinterpreter.kernel_exceptions import TwinterpeterUnavailable


# current twin state
#: the kernel(s) running in this interpeter
KERNELS = {}
#: id of this interpreter/process
TWIN_ID = os.path.basename(sys.executable)
#: id of the main interpeter
MASTER_ID = TWIN_ID


def is_twinterpreter(kernel_id):
    """Check whether this interpreter is running a specific kernel"""
    return TWIN_ID == kernel_id


def get_kernel(kernel_id):
    """
    Get this interpreter's interface to a specific kernel

    :param kernel_id: id of the desired kernel
    :type kernel_id: str, TWIN_MASTER or TWIN_ONLY_SLAVE

    :raises: :py:class:`~.TwinterpeterUnavailable` if no active kernel matches `kernel_id`
    :raises: RuntimeError if :py:class:`TWIN_ONLY_SLAVE` is requested but there are multiple kernels
    """
    assert not is_twinterpreter(kernel_id), 'Attempted call to own interpeter'
    try:
        return KERNELS[kernel_id]
    except KeyError:
        raise TwinterpeterUnavailable(twin_id=kernel_id)
