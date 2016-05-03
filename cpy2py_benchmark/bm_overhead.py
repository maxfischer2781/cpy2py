# coding=utf-8
from __future__ import print_function
import time
import math
import sys
import os

from cpy2py import TwinMaster
from cpy2py.utility.compat import rangex
from cpy2py.utility.proc_tools import get_executable_path
import argparse


class TimingVector(object):
    def __init__(self):
        self._values = []

    @property
    def average(self):
        if not self._values:
            return None
        return sum(self._values) / len(self._values)

    @property
    def error(self):
        avg = self.average
        if not avg:
            return None
        return math.sqrt(sum((val - avg)**2 for val in self._values)) / len(self._values)

    def pushback(self, value):
        self._values.append(value)

    def __str__(self):
        if sys.version_info > (2,):
            return self.__unicode__()
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        avg = self.average
        err = self.error
        if avg is None:
            return u' --  ± ---- s'
        elif avg >= 1.0:
            return u'%3d ±%3d.%1d s' % (avg, err, (err * 10) % 10)
        elif avg > 0.001:
            return u'%3d ±%3d.%1d ms' % (avg * 1E3, err * 1E3, (err * 1E4) % 10)
        elif avg > 0.000001:
            return u'%3d ±%3d.%1d us' % (avg * 1E6, err * 1E6, (err * 1E7) % 10)
        elif avg > 0.000000001:
            return u'%3d ±%3d.%1d ns' % (avg * 1E9, err * 1E9, (err * 1E10) % 10)


def time_overhead(executable, count, total, call, reply):
    # prepare kernel
    twinterpreter = TwinMaster(executable=executable, twinterpreter_id='other')
    twinterpreter.start()
    for _ in rangex(count):
        # test
        start_time = time.time()
        twin_time = twinterpreter.execute(time.time)
        end_time = time.time()
        total.pushback(end_time - start_time)
        call.pushback(twin_time - start_time)
        reply.pushback(end_time - twin_time)
    # cleanup
    twinterpreter.destroy()


def main():
    cli = argparse.ArgumentParser(
        "Test overhead for dispatching function calls"
    )
    cli.add_argument(
        '--repeats',
        nargs='+',
        help='Tests to run in the form <count>:<tries>:<name>. [%(default)s]',
        default=['15000:15:15x15k', '5000:30:30x5k', '1:50:50x1', '1:1500:1.5kx1']
    )
    cli.add_argument(
        '--interpreter',
        nargs='+',
        help='Interpreters to use. [%(default)s]',
        default=['pypy', 'pypy3', 'python2.6', 'python2.7', 'python3.4']
    )
    settings = cli.parse_args()
    interpreters = settings.interpreter
    for interpreter in interpreters[:]:
        try:
            _ = get_executable_path(interpreter)
        except OSError as err:
            interpreters.remove(interpreter)
            print("Ignoring interpreter:", interpreter, err.__class__.__name__, err)
    repeats = []
    for test in settings.repeats:
        test = test.split(':', 2)
        repeats.append((int(test[0]), int(test[1]), test[2]))
    results = {}
    for count, tries, name in repeats:
        results[name] = {}
        for interpreter in interpreters:
            total, call, reply = TimingVector(), TimingVector(), TimingVector()
            for idx in rangex(tries):
                sys.stdout.write(' '.join(('Test', name, '=>', interpreter, str(idx), '/', str(tries), ' ' * 20, '\r')))
                sys.stdout.flush()
                time_overhead(interpreter, count, total, call, reply)
            results[name][interpreter] = total, call, reply
        print('Test', name, 'Done', ' ' * 80)
    print("=" * 20, "=" * 20, "=" * 20, "=" * 20)
    print('%20s %20s %20s %20s' % ('interpreter', 'total', 'call', 'reply'))
    print("=" * 20, "=" * 20, "=" * 20, "=" * 20)
    for _, _, name in repeats:
        for key in interpreters:
            tot, call, reply = results[name][key]
            print(u'%10s [%7s] %20s %20s %20s' % (key, name, tot, call, reply))
        print("=" * 20, "=" * 20, "=" * 20, "=" * 20)
    print('\n\n\n')
    print(*(["=" * 20] * (len(repeats) + 1)))
    print(os.path.splitext(os.path.basename(sys.executable))[0].rjust(20), *['%20s' % name for _, _, name in repeats])
    print(*(["=" * 20] * (len(repeats) + 1)))
    for key in interpreters:
        print(key.rjust(20), end=" ")
        for _, _, name in repeats:
            print(u'%20s' % results[name][key][0], end=" ")
        print("")
    print(*(["=" * 20] * (len(repeats) + 1)))
    print('\n\n\n')

if __name__ == "__main__":
    main()
