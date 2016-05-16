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
import argparse
import sys
import base64
import os
import logging

from cpy2py.utility.compat import pickle, str_to_bytes
from cpy2py.kernel import kernel_single, kernel_state
from cpy2py.kernel.kernel_exceptions import TwinterpeterTerminated


DEFAULT_PKL_PROTO = 2  # prot2 is supported by all supported versions


# storing and loading of initial state
def dump_any(obj):
    """Default for dumping arbitrary objects to CLI"""
    return base64.b64encode(pickle.dumps(obj, DEFAULT_PKL_PROTO))


def load_any(obj_pkl):
    """Default for loading arbitrary objects from CLI"""
    return pickle.loads(base64.b64decode(str_to_bytes(obj_pkl)))


def dump_connector(connector):
    """Dump an IPyC connection connector"""
    return dump_any(connector)


def load_connector(connector_pkl):
    """Create an IPyC connection from a connector pickle"""
    connector = load_any(connector_pkl)
    return connector[0](*connector[1], **connector[2])


def dump_kernel(kernel_client, kernel_server):
    """Dump kernel client and server classes"""
    return dump_any((kernel_client, kernel_server))


def load_kernel(kernel_pkl):
    """Load kernel client and server classes"""
    if kernel_pkl is None:
        return None
    return load_any(kernel_pkl)


def dump_initializer(initializers):
    """Dump initializer functions"""
    initializer_pkls = []
    for initializer in initializers:
        initializer_pkls.append(dump_any(initializer))
    return initializer_pkls


def run_initializer(initializer_pkls):
    """Run initializer functions"""
    for initializer_pkl in initializer_pkls:
        initializer = load_any(initializer_pkl)
        # run immediately in case there are dependencies during unpickling
        initializer()


def dump_main_def(main_def):
    """Dump the main module"""
    return dump_any(main_def)


def run_main_def(main_def_pkl):
    """Bootstrap a main module"""
    if main_def_pkl is None:
        return
    main_def = load_any(main_def_pkl)
    return main_def.bootstrap()


def bootstrap_kernel():
    """
    Deploy a kernel to make this interpreter a twinterpreter

    :see: This script is invoked by
          :py:class:`~cpy2py.twinterpreter.twin_master.TwinMaster`
          to launch a twinterpreter.
    """
    parser = argparse.ArgumentParser("Python Twinterpreter Kernel")
    # identification
    parser.add_argument(
        '--peer-id',
        help="unique identifier for our owner",
    )
    parser.add_argument(
        '--twin-id',
        help="unique identifier for this twinterpreter",
    )
    parser.add_argument(
        '--master-id',
        help="unique identifier for the master twinterpreter",
    )
    # communication
    parser.add_argument(
        '--server-ipyc',
        help="base 64 encoded pickled server connection",
    )
    parser.add_argument(
        '--client-ipyc',
        help="base 64 encoded pickled client connection",
    )
    parser.add_argument(
        '--ipyc-pkl-protocol',
        help="pickle protocol to use for IPyC",
        type=int,
    )
    parser.add_argument(
        '--kernel',
        help="base 64 encoded kernel client and server class",
    )
    # internal environment
    parser.add_argument(
        '--main-def',
        help="base 64 encoded main module bootstrap",
    )
    parser.add_argument(
        '--cwd',
        help="current work dir to use",
    )
    parser.add_argument(
        '--initializer',
        nargs='*',
        help="base 64 encoded initialization functions",
        default=[],
    )
    settings = parser.parse_args()
    assert kernel_state.TWIN_ID == settings.twin_id
    assert kernel_state.MASTER_ID == settings.master_id
    # setup parent environment/namespace first
    if settings.cwd:
        os.chdir(settings.cwd)
    run_main_def(settings.main_def)
    # run initializers before creating any resources
    # TwinMaster will run the finalizers directly
    run_initializer(settings.initializer)
    exit_code = run_kernel(
        kernel=load_kernel(settings.kernel),
        client_ipyc=load_connector(settings.client_ipyc),
        server_ipyc=load_connector(settings.server_ipyc),
        peer_id=settings.peer_id,
        ipyc_pkl_protocol=settings.ipyc_pkl_protocol
    )
    logging.getLogger('__cpy2py__.kernel.%s_to_%s.bootstrap' % (kernel_state.TWIN_ID, settings.peer_id)).warning(
        '[%s] %s.bootstrap_kernel exiting with %s', kernel_state.TWIN_ID, __name__, exit_code
    )
    sys.exit(exit_code)


def run_kernel(kernel, client_ipyc, server_ipyc, peer_id, ipyc_pkl_protocol):
    # start in opposite order as TwinMaster to avoid deadlocks
    if kernel:
        client, server = kernel
    else:
        client, server = kernel_single.CLIENT, kernel_single.SERVER
    kernel_server = server(
        peer_id=peer_id,
        ipyc=server_ipyc,
        pickle_protocol=ipyc_pkl_protocol,
    )
    kernel_client = client(
        peer_id=peer_id,
        ipyc=client_ipyc,
        pickle_protocol=ipyc_pkl_protocol,
    )
    exit_code = kernel_server.run()
    try:
        kernel_client.stop()
    except TwinterpeterTerminated:
        pass
    return exit_code


if __name__ == "__main__":
    bootstrap_kernel()
