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
import os
import random
import time
import sys

from cpy2py.twinterpreter.kernel_exceptions import TwinterpeterUnavailable
from cpy2py.utility.enum import UniqueObj


# shorthands for special kernels
class TwinMaster(UniqueObj):
    """The master twinterpeter"""
    name = '<Master Kernel>'


class TwinOnlySlave(UniqueObj):
    """The slave twinterpeter, if unambigous"""
    name = '<Single Twin Kernel>'


# current twin state
#: the kernel(s) running in this interpeter
__kernels__ = {}
#: id of this interpreter/process
__twin_id__ = os.path.basename(sys.executable)
#: id of the main interpeter
__master_id__ = __twin_id__
#: id of the active group of twinterpeters
__twin_group_id__ = '%08X%08X%08X' % (
    time.time() * 16,
    os.getpid(),
    random.random() * pow(16, 8)
)


def is_twinterpreter(kernel_id=TwinOnlySlave):
    """Check whether this interpreter is running a specific kernel"""
    if kernel_id is TwinMaster:
        return __twin_id__ == __master_id__
    if kernel_id is TwinOnlySlave:
        if len(__kernels__) != 1:
            raise RuntimeError(
                "Twinterpeter kernel_id '%s' is ambigious if there isn't exactly one slave." % TwinOnlySlave)
        return __twin_id__ != __master_id__
    return __twin_id__ == kernel_id


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
        if kernel_id is TwinMaster:
            return __kernels__[__master_id__]
        if kernel_id is TwinOnlySlave:
            if len(__kernels__) != 1:
                raise RuntimeError(
                    "Twinterpeter kernel_id '%s' is ambigious if there isn't exactly one slave." % TwinOnlySlave)
            return __kernels__.keys()[0]
        return __kernels__[kernel_id]
    except KeyError:
        raise TwinterpeterUnavailable(twin_id=kernel_id)
