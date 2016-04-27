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

This module is auto-initialized as part of the :py:mod:`cpy2py` import.
Slaved twinterpreters are initialized via
:py:func:`~cpy2py.twinterpreter.bootstrap.bootstrap_kernel` on startup.

If you wish to change :py:data:`TWIN_ID` of the main process, you must
do so via environment variables:

.. envvar:: __CPY2PY_TWIN_ID__

   Identifier of this interpreter. If defined before starting a
   :py:mod:`cpy2py` application, the master's identifier. It defaults
   to ``os.path.basename(sys.executable)``.

.. envvar:: __CPY2PY_MASTER_ID__

   Identifier of the master interpreter. Do not set this explicitly.
"""
import os
import sys

from cpy2py.kernel.kernel_exceptions import TwinterpeterUnavailable


# current twin state
#: the kernel client(s) running in this interpeter
KERNEL_CLIENTS = {}
#: the kernel servers(s) running in this interpeter
KERNEL_SERVERS = {}
#: low-level interface to dispatch commands to a kernel
KERNEL_INTERFACE = {}
#: id of this interpreter/process
TWIN_ID = os.environ.pop('__CPY2PY_TWIN_ID__', os.path.basename(sys.executable))
#: id of the main interpeter
MASTER_ID = os.environ.pop('__CPY2PY_MASTER_ID__', TWIN_ID)
#: shared state of all twinterpreters
TWIN_GROUP_STATE = None


def is_twinterpreter(kernel_id):
    """Check whether this interpreter is running a specific kernel"""
    return TWIN_ID == kernel_id


def is_master():
    """Check whether this interpreter is the group master"""
    return is_twinterpreter(MASTER_ID)


def get_kernel(kernel_id):
    """
    Get this interpreter's client to a specific kernel

    :param kernel_id: id of the desired kernel
    :type kernel_id: str, TWIN_MASTER or TWIN_ONLY_SLAVE

    :raises: :py:class:`~.TwinterpeterUnavailable` if no active kernel matches `kernel_id`
    :raises: RuntimeError if :py:class:`TWIN_ONLY_SLAVE` is requested but there are multiple kernels
    """
    assert not is_twinterpreter(kernel_id), 'Attempted call to own interpeter'
    try:
        return KERNEL_INTERFACE[kernel_id]
    except KeyError:
        raise TwinterpeterUnavailable(twin_id=kernel_id)
