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
import cpy2py.twinterpreter.kernel
import cpy2py.twinterpreter.kernel_state


def dump_connector(connector):
    """Dump an IPyC connection connector"""
    return base64.b64encode(pickle.dumps(connector, 2))  # prot2 is supported by all supported versions


def load_connector(connector_pkl):
    """Create an IPyC connection from a connector pickle"""
    connector = pickle.loads(base64.b64decode(connector_pkl))
    return connector[0](*connector[1], **connector[2])


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
    settings = parser.parse_args()
    cpy2py.twinterpreter.kernel_state.TWIN_ID = settings.twin_id
    cpy2py.twinterpreter.kernel_state.MASTER_ID = settings.master_id
    server_ipyc = load_connector(settings.server_ipyc)
    client_ipyc = load_connector(settings.client_ipyc)
    # start in opposite order as TwinMaster to avoid deadlocks
    kernel_server = cpy2py.twinterpreter.kernel.SingleThreadKernelServer(
        peer_id=settings.peer_id,
        ipyc=server_ipyc,
        pickle_protocol=settings.ipyc_pkl_protocol,
    )
    kernel_client = cpy2py.twinterpreter.kernel.SingleThreadKernelClient(
        peer_id=settings.peer_id,
        ipyc=client_ipyc,
        pickle_protocol=settings.ipyc_pkl_protocol,
    )
    exit_code = kernel_server.run()
    kernel_client.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    bootstrap_kernel()
