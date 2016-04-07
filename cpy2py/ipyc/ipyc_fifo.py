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
import atexit
import os
import shutil
import tempfile


class DuplexFifoIPyC(object):
    """Duplex FIFO exporting file-like interface"""
    def __init__(self, fifo_dir_path=None, is_master=True):
        self._fifo_dir_path = fifo_dir_path
        if fifo_dir_path is None:
            self._fifo_dir_path = tempfile.mkdtemp()
            atexit.register(shutil.rmtree, self._fifo_dir_path)
        self.is_master = is_master
        if is_master:
            self._fifo_read_path = os.path.join(self._fifo_dir_path, 'cpy2py_s2c.ipc')
            self._fifo_write_path = os.path.join(self._fifo_dir_path, 'cpy2py_c2s.ipc')
            os.mkfifo(self._fifo_read_path)
            os.mkfifo(self._fifo_write_path)
        else:
            self._fifo_read_path = os.path.join(self._fifo_dir_path, 'cpy2py_c2s.ipc')
            self._fifo_write_path = os.path.join(self._fifo_dir_path, 'cpy2py_s2c.ipc')
        self._fifo_read = None
        self._fifo_write = None

    def open(self):
        """Open connections"""
        # open opposites first to avoid deadlock
        if self.is_master:
            self._fifo_read = open(self._fifo_read_path, 'r', 0)
            self._fifo_write = open(self._fifo_write_path, 'w', 0)
        else:
            self._fifo_write = open(self._fifo_write_path, 'w', 0)
            self._fifo_read = open(self._fifo_read_path, 'r', 0)

    def close(self):
        """Close connections"""
        self._fifo_read.close()
        self._fifo_write.close()

    def read(self, size=None):
        """Read at most `size` bytes"""
        if size is None:
            return self._fifo_read.read()
        else:
            return self._fifo_read.read(size)

    def readline(self):
        """Read one entire line"""
        return self._fifo_read.readline()

    def write(self, message):
        """Write a string"""
        return self._fifo_write.write(message)

    @property
    def connector(self):
        """Pickle'able connector as (factory, args, kwargs)"""
        return self.__class__, (), {'fifo_dir_path': self._fifo_dir_path, 'is_master': False}

    def __repr__(self):
        return '%s(fifo_dir_path=%r, is_master=%s)' % (self.__class__.__name__, self._fifo_dir_path, self.is_master)
