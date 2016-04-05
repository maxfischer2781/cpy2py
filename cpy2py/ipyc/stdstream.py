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
import sys
import cPickle as pickle
from cpy2py.ipyc import ipyc_file


class StdIPC(ipyc_file.FileIPyC):
    """
    IPyC using streams, defaulting to :py:class:`sys.stdin` and :py:class:`sys.stdout`

    :param readstream: file-like object to receive messages from
    :param writestream: file-like object to write messages to
    :param pickler_cls: serializer class, according to :py:mod:`pickle`
    :param unpickler_cls: deserializer class, according to :py:mod:`pickle`
    :param pickle_protocol: pickling protocol to use
    """
    def __init__(
            self,
            readstream=sys.stdin,
            writestream=sys.stdout,
            persistent_id=None,
            persistent_load=None,
            pickle_protocol=pickle.HIGHEST_PROTOCOL
    ):
        ipyc_file.FileIPyC.__init__(
            self,
            read_file=readstream,
            write_file=writestream,
            persistent_id=persistent_id,
            persistent_load=persistent_load,
            pickle_protocol=pickle_protocol
        )
