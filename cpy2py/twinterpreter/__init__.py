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
Alternative interpreters deployed in parallel
"""
# bootstrap group state
from cpy2py.kernel import kernel_state
from cpy2py.twinterpreter import group_state


def _register_twin_group_state(twin_group_state):
    kernel_state.TWIN_GROUP_STATE = twin_group_state


if kernel_state.is_master():
    TGS = group_state.TwinGroupState()
    _register_twin_group_state(TGS)
    TGS.add_finalizer(_register_twin_group_state, TGS)
    del TGS
