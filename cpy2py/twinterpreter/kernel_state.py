# - # Copyright 2016 Max Fischer
# - #
# - # Licensed under the Apache License, Version 2.0 (the "License");
# - # you may not use this file except in compliance with the License.
# - # You may obtain a copy of the License at
# - #
# - # 	http://www.apache.org/licenses/LICENSE-2.0
# - #
# - # Unless required by applicable law or agreed to in writing, software
# - # distributed under the License is distributed on an "AS IS" BASIS,
# - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# - # See the License for the specific language governing permissions and
# - # limitations under the License.
import os
import random
import time

from cpy2py.twinterpreter.kernel_exceptions import TwinterpeterUnavailable
from cpy2py.utility.enum import UniqueObj


# shorthands for special kernels
class TWIN_MASTER(UniqueObj):
	"""The master twinterpeter"""
	name = '<Master Kernel>'


class TWIN_ONLY_SLAVE(UniqueObj):
	"""The slave twinterpeter, if unambigous"""
	name = '<Single Twin Kernel>'


# current twin state
#: the kernel(s) running in this interpeter
__kernels__ = {}
#: id of this interpreter/process
__twin_id__ = 'main'
#: whether this is the parent process
__is_master__ = True
#: id of the active group of twinterpeters
__twin_group_id__ = '%08X%08X%08X' % (
	time.time() * 16,
	os.getpid(),
	random.random() * pow(16, 8)
)


def is_twinterpreter(kernel_id=TWIN_ONLY_SLAVE):
	"""Check whether this interpreter is running a specific kernel"""
	if kernel_id is TWIN_MASTER:
		return __is_master__
	if kernel_id is TWIN_ONLY_SLAVE:
		if len(__kernels__) != 1:
			raise RuntimeError("Twinterpeter kernel_id '%s' is ambigious if there isn't exactly one slave." % TWIN_ONLY_SLAVE)
		return not __is_master__
	return __twin_id__ == kernel_id


def get_kernel(kernel_id):
	"""
	Get this interpreter's interface to a specific kernel

	:param kernel_id: id of the desired kernel
	:type kernel_id: str, TWIN_MASTER or TWIN_ONLY_SLAVE

	:raises TwinterpeterUnavailable: if no active kernel matches `kernel_id`
	:raise RuntimeError: if :py:class:`TWIN_ONLY_SLAVE` is requested but there are multiple kernels
	"""
	assert not is_twinterpreter(kernel_id), 'Attempted call to own interpeter'
	try:
		if kernel_id is TWIN_MASTER:
			return __kernels__['main']
		if kernel_id is TWIN_ONLY_SLAVE:
			if len(__kernels__) != 1:
				raise RuntimeError("Twinterpeter kernel_id '%s' is ambigious if there isn't exactly one slave." % TWIN_ONLY_SLAVE)
			return __kernels__.keys()[0]
		return __kernels__[kernel_id]
	except KeyError:
		raise TwinterpeterUnavailable(twin_id=kernel_id)
