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
import cpy2py.utility.exceptions


class TwinterpeterException(cpy2py.utility.exceptions.CPy2PyException):
    """Exception in Twinterpeter internals"""
    pass


class TwinterpeterUnavailable(TwinterpeterException, RuntimeError):
    """A requested Twinterpeter is not available, e.g. because it has not bee started"""
    def __init__(self, twin_id):
        TwinterpeterException.__init__(self, "Twinterpeter '%s' not available" % twin_id)
        self.twin_id = twin_id


class TwinterpeterTerminated(TwinterpeterUnavailable):
    """A requested Twinterpeter is not available, because it was terminated already"""
    def __init__(self, twin_id):
        TwinterpeterException.__init__(self, "Twinterpeter '%s' already terminated" % twin_id)
        self.twin_id = twin_id
