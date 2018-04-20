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
Control and Management of additional interpreters deployed in parallel

This module is tasked with managing the actual interpreter - its process and environment.
It is meant to start, initialise, finalise and stop interpreters.
While running, the :py:mod:`~cpy2py.kernel` module handles the interaction between interpreters.
"""
import logging
# bootstrap group state
from cpy2py.kernel import state
from cpy2py.twinterpreter import group_state


def _register_twin_group_state(twin_group_state):
    state.TWIN_GROUP_STATE = twin_group_state


if state.is_master():
    TGS = group_state.TwinGroupState()
    _register_twin_group_state(TGS)
    TGS.add_finalizer(_register_twin_group_state, TGS)
    del TGS


# plugins
def _bootstrap_coverage():
    logger = logging.getLogger('__cpy2py__.bootstrap.plugin.coverage')
    try:
        import coverage
        logger.info('plugin coverage available')
    except ImportError:
        logger.warning('plugin coverage unavailable')
    else:
        coverage.process_startup()
        if hasattr(coverage.process_startup, "done"):
            logger.info('plugin coverage enabled')
        else:
            logger.info('plugin coverage disabled')


if state.is_master():
    state.TWIN_GROUP_STATE.add_initializer(_bootstrap_coverage)
