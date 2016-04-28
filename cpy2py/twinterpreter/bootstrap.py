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

from cpy2py.utility.compat import pickle
from cpy2py.kernel import kernel_single, kernel_state


DEFAULT_PKL_PROTO = 2  # prot2 is supported by all supported versions


def dump_connector(connector):
    """Dump an IPyC connection connector"""
    return base64.b64encode(pickle.dumps(connector, DEFAULT_PKL_PROTO))


def load_connector(connector_pkl):
    """Create an IPyC connection from a connector pickle"""
    connector = pickle.loads(base64.b64decode(connector_pkl))
    return connector[0](*connector[1], **connector[2])


def dump_kernel(kernel_client, kernel_server):
    """Dump kernel client and server classes"""
    return base64.b64encode(pickle.dumps((kernel_client, kernel_server), DEFAULT_PKL_PROTO))


def load_kernel(kernel_pkl):
    """Load kernel client and server classes"""
    return pickle.loads(base64.b64decode(kernel_pkl))


def dump_initializer(initializers):
    """Dump initializer functions"""
    initializer_pkls = []
    for initializer in initializers:
        initializer_pkls.append(base64.b64encode(pickle.dumps(initializer, DEFAULT_PKL_PROTO)))
    return initializer_pkls


def run_initializer(initializer_pkls):
    """Run initializer functions"""
    for initializer_pkl in initializer_pkls:
        initializer = pickle.loads(base64.b64decode(initializer_pkl))
        initializer()


def bootstrap_kernel():
    """
    Deploy a kernel to make this interpreter a twinterpreter

    :see: This script is invoked by
          :py:class:`~cpy2py.twinterpreter.twin_master.TwinMaster`
          to launch a twinterpreter.
    """
    parser = argparse.ArgumentParser("Python Twinterpreter Kernel")
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
    parser.add_argument(
        '--initializer',
        nargs='*',
        help="base 64 encoded initialization functions",
        default=[],
    )
    settings = parser.parse_args()
    assert kernel_state.TWIN_ID == settings.twin_id
    assert kernel_state.MASTER_ID == settings.master_id
    # run initializers before creating any resources
    run_initializer(settings.initializer)
    server_ipyc = load_connector(settings.server_ipyc)
    client_ipyc = load_connector(settings.client_ipyc)
    # use custom kernels
    if settings.kernel:
        client, server = load_kernel(settings.kernel)
    else:
        client, server = kernel_single.CLIENT, kernel_single.SERVER
    # start in opposite order as TwinMaster to avoid deadlocks
    kernel_server = server(
        peer_id=settings.peer_id,
        ipyc=server_ipyc,
        pickle_protocol=settings.ipyc_pkl_protocol,
    )
    kernel_client = client(
        peer_id=settings.peer_id,
        ipyc=client_ipyc,
        pickle_protocol=settings.ipyc_pkl_protocol,
    )
    exit_code = kernel_server.run()
    kernel_client.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    bootstrap_kernel()
