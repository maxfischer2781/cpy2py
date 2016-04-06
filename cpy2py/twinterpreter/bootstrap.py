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
import os
import logging
import sys
import cPickle as pickle

import cpy2py.twinterpreter.kernel
import cpy2py.twinterpreter.kernel_state


def load_connector(connector_pkl):
    """Create an IPyC connection from a connector pickle"""
    connector = pickle.loads(connector_pkl)
    return connector[0](*connector[1], **connector[2])


def bootstrap_kernel():
    """
    Deploy a kernel to make this interpreter a twinterpreter
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
        help="pickled server connection",
    )
    parser.add_argument(
        '--client-ipyc',
        help="pickled client connection",
    )
    settings = parser.parse_args()
    logging.getLogger().addHandler(
        logging.FileHandler(filename='%s.%s' % (os.path.basename(sys.executable), settings.peer_id)))
    cpy2py.twinterpreter.kernel_state.twin_id = settings.twin_id
    cpy2py.twinterpreter.kernel_state.master_id = settings.master_id
    server_ipyc = load_connector(settings.server_ipyc)
    client_ipyc = load_connector(settings.client_ipyc)
    kernel = cpy2py.twinterpreter.kernel.SingleThreadKernel(
        peer_id=settings.peer_id,
        server_ipyc=server_ipyc,
        client_ipyc=client_ipyc,
    )
    sys.exit(kernel.run())


if __name__ == "__main__":
    bootstrap_kernel()
