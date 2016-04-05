import cPickle as pickle
from cpy2py.ipyc.ipyc_exceptions import IPyCTerminated


class FileIPyC(object):
    """
    IPyC using file-like objects

    :param read_file: file-like object to receive messages from
    :param write_file: file-like object to write messages to
    :param persistent_id: `persistent_id` for :py:class:`pickle.Pickler`
    :param persistent_load: `persistent_load` for :py:class:`pickle.Unpickler`
    :param pickle_protocol: pickling protocol to use

    :warning: This class can be manually setup, but the cpy2py ecosystem
              expects :py:attr:`connector` to be valid. It should be
              considered a baseclass.
    """
    def __init__(
            self,
            read_file,
            write_file,
            persistent_id=None,
            persistent_load=None,
            pickle_protocol=pickle.HIGHEST_PROTOCOL
    ):
        self._read_file = read_file
        self._write_file = write_file
        self._persistent_id = persistent_id
        self._persistent_load = persistent_load
        self._pkl_protocol = pickle_protocol
        # patch un-/pickler and shortcut their load/dump
        self._pickler = pickle.Pickler(self._write_file, self._pkl_protocol)
        self._pickler.persistent_id = self._persistent_id
        self._dump = self._pickler.dump
        self._unpickler = pickle.Unpickler(self._read_file)
        self._unpickler.persistent_load = self._persistent_load
        self._load = self._unpickler.load

    def bind(self):
        """Begin communication"""
        pass

    def send(self, payload):
        """Send an object"""
        try:
            self._dump(payload)
            self._write_file.flush()
        except IOError:
            raise IPyCTerminated

    def receive(self):
        """Receive an object"""
        try:
            return self._load()
        except EOFError:
            raise IPyCTerminated

    @property
    def connector(self):
        """Pickle'able object capable of connecting to this interface"""
        raise NotImplementedError
