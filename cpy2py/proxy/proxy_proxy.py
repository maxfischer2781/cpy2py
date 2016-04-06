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
from cpy2py.proxy.proxy_object import TwinObject
from cpy2py.twinterpreter import kernel_state


class ProxyProxy(TwinObject):
    """
    Helper for proxying objects existing in the current twinterpeter

    :warning: This class is experimental at the moment.
    """
    # always stay in current twinterpeter
    __twin_id__ = kernel_state.TWIN_ID

    def __init__(self, real_object):
        TwinObject.__setattr__(self, '_real_object', real_object)

    def __getattr__(self, name):
        return getattr(self._real_object, name)

    def __setattr__(self, name, value):
        return setattr(self._real_object, name, value)

    def __delattr__(self, name):
        return delattr(self._real_object, name)
