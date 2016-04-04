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
Multi-intepreter execution environment

`cpy2py` let's the CPython and PyPy interpreters see eye to eye. In parallel to
the main interpreter, another interpreter is run to execute parts of the
application.
"""

from cpy2py.proxy.proxy_object import TwinObject
from cpy2py.twinterpreter.twin_master import TwinMaster
from cpy2py.twinterpreter import kernel_state

__all__ = ['TwinObject', 'TwinMaster', 'kernel_state']
