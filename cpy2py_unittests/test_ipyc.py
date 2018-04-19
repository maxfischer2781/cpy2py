import unittest
import time

from cpy2py import state, TwinMaster, TwinObject
from cpy2py.utility.compat import range
from cpy2py.ipyc import ipyc_fifo, ipyc_socket


class PrimitiveObject(TwinObject):
    __twin_id__ = 'pypy_multi'

    def mod(self, num=0, mod=1):
        return self.__twin_id__ == state.TWIN_ID, num % mod


class TestIpycDefault(unittest.TestCase):
    def setUp(self):
        self.twinterpreter = TwinMaster(executable='pypy', twinterpreter_id='pypy_multi', kernel='multi')
        self.twinterpreter.start()

    def tearDown(self):
        self.twinterpreter.destroy()
        time.sleep(0.1)

    def test_one(self):
        my_instance = PrimitiveObject()
        self.assertEqual((True, 0), my_instance.mod(5))

    def test_lots(self):
        for reps in range(1, 51, 10):
            my_instance = PrimitiveObject()
            for _ in range(reps):
                self.assertEqual((True, 0), my_instance.mod(5))
            del my_instance


class TestIpycFifo(TestIpycDefault):
    def setUp(self):
        self.twinterpreter = TwinMaster(
            executable='pypy', twinterpreter_id='pypy_multi', kernel='multi', ipyc=ipyc_fifo.DuplexFifoIPyC
        )
        self.twinterpreter.start()


class TestIpycSocket(TestIpycDefault):
    def setUp(self):
        self.twinterpreter = TwinMaster(
            executable='pypy', twinterpreter_id='pypy_multi', kernel='multi', ipyc=ipyc_socket.DuplexSocketIPyC
        )
        self.twinterpreter.start()

