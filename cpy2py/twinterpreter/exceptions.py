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
# pylint: disable=too-many-ancestors,non-parent-init-called,super-init-not-called
from cpy2py.utility.exceptions import CPy2PyException


class TwinterpreterException(CPy2PyException):
    """Exceptions relating to Twinterpreter"""
    pass


class TwinterpreterProcessError(TwinterpreterException):
    """Error relating to a Twinterpreter process"""
    pass


class RemoteCpy2PyNotFound(ImportError, CPy2PyException):
    """Module ``cpy2py`` not available in twinterpreter"""
    def __init__(self, interpreter):
        self.name = 'cpy2py'
        self.interpreter = interpreter
        super(RemoteCpy2PyNotFound, self).__init__("No module named 'cpy2py' available for %r" % interpreter)
