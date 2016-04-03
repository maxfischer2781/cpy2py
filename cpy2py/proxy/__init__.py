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
Proxies to objects in a twinterpreter

Proxies are the local interpreter's interface to objects living in a twin's
domain.
"""

from cpy2py.proxy.proxy_tracker import twin_pickler, twin_unpickler
from cpy2py.proxy.proxy_object import TwinObject

__all__ = ['twin_pickler', 'twin_unpickler', 'TwinObject']
