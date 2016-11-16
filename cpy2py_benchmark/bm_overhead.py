# coding=utf-8
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

    @property
    def min(self):
        if not self._values:
            return None
        return min(self._values)

    @property
    def max(self):
        if not self._values:
            return None
        return max(self._values)

    def pushback(self, value):
        self._values.append(value)

    def long_str(self):
        return u'%s %s' % (
            self,
            self.range_str()
        )

    def range_str(self):
        return u'[%s…%s]' % (
            self.time_repr(self.min),
            self.time_repr(self.max)
        )

    def __str__(self):
        if sys.version_info > (2,):
            return self.__unicode__()
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'%s ± %s' % (self.time_repr(self.average), self.time_repr(self.error))

    @staticmethod
    def time_repr(num):
        if num is None:
            return '---  s'
        if num == 0:
            return '0.0  s'
        e_power = 18
        for t_power, prefix in enumerate(u'EPTGMk mμnpfa'):
            power = e_power - t_power * 3
            p_num = num / (10 ** power)
            if 1E3 > p_num > 1.0:
                if p_num > 100:
                    return '%3.0f %ss' % (p_num, prefix)
                if p_num > 10:
                    return '%2.0f. %ss' % (p_num, prefix)
                return '%3.1f %ss' % (p_num, prefix)


def time_overhead(executable, count, total, call, reply, kernel):
    # prepare kernel
    twinterpreter = TwinMaster(executable=executable, twinterpreter_id='other', kernel=kernel)
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
        default=['15000:15:15x15k', '5000:30:30x5k', '1:50:50x1']
    )
    cli.add_argument(
        '--interpreters',
        nargs='+',
        help='Interpreters to use. [%(default)s]',
        default=['pypy', 'pypy3', 'python2.6', 'python2.7', 'python3.3', 'python3.4', 'python3.5']
    )
    cli.add_argument(
        '--kernels',
        nargs='+',
        help='Kernel modules to use as <module>[:<name>]. [%(default)s]',
        default=['cpy2py.kernel.kernel_async:async', 'cpy2py.kernel.kernel_single:single']
    )
    settings = cli.parse_args()
    interpreters = []
    for interpreter in settings.interpreters:
        try:
            _ = get_executable_path(interpreter)
            interpreters.append(interpreter)
        except OSError as err:
            print("Ignoring interpreter:", interpreter, err.__class__.__name__, err)
    kernels = []
    for kernel in settings.kernels:
        module, _, nick = kernel.partition(':')
        __import__(module)
        nick = nick or module.rsplit('.', 1)[-1]
        kernels.append((sys.modules[module], nick))
    repeats = []
    for test in settings.repeats:
        test = test.split(':', 2)
        repeats.append((int(test[0]), int(test[1]), test[2]))
    results = {}
    start_time = time.time()
    for count, tries, name in repeats:
        results[name] = {}
        strat_time_tries = time.time()
        for interpreter in interpreters:
            results[name][interpreter] = {}
            for kernel, kname in kernels:
                total, call, reply = TimingVector(), TimingVector(), TimingVector()
                for idx in rangex(tries):
                    sys.stdout.write(' '.join((
                        # what
                        'Test',
                        name.rjust(15),
                        kname.rjust(15),
                        '=>',
                        interpreter,
                        # progress
                        str(idx),
                        '/',
                        str(tries),
                        # timing
                        total.long_str(),
                        # filler
                        ' ' * 20,
                        '\r'
                    )))
                    sys.stdout.flush()
                    time_overhead(interpreter, count, total, call, reply, kernel)
                results[name][interpreter][kname] = total, call, reply
        print('Test', name.rjust(15), 'Done', '%.1f' % (time.time() - strat_time_tries), ' ' * 80)
        print_results(
            start_time=start_time,
            results=results,
            repeats=[rp[2] for rp in repeats],
            kernels=[kn[1] for kn in kernels],
            interpreters=interpreters,
        )


def print_results(start_time, results, repeats=None, kernels=None, interpreters=None):
    repeats = repeats or list(results)
    interpreters = interpreters or list(results[repeats[0]])
    kernels = kernels or list(results[repeats[0]][interpreters[0]])
    print('Test', 'all'.rjust(15), 'Done', '%.1f' % (time.time() - start_time))
    print("=" * 20, "=" * 20, "=" * 20, "=" * 20)
    print('%20s %20s %20s %20s' % ('interpreter', 'total', 'call', 'reply'))
    print("=" * 20, "=" * 20, "=" * 20, "=" * 20)
    for name in repeats:
        for kname in kernels:
            for key in interpreters:
                tot, call, reply = results[name][key][kname]
                print(u'%10s [%7s] %20s %20s %20s' % (key, name, tot, call, reply))
            print("=" * 20, "=" * 20, "=" * 20, "=" * 20)
    print('\n\n\n')
    print(*(["=" * 20] * (len(kernels) * len(repeats) + 1)))
    print(os.path.splitext(os.path.basename(sys.executable))[0].rjust(20), end=' ')
    for kname in kernels:
        print(kname.rjust(20), *(['\\' + (' ' * 19)] * (len(repeats) - 1)), end=' ')
    print('')
    print(
        '\\' + (' ' * 19),
        *(['%20s' % name for name in repeats] * len(kernels)))
    print(*(["=" * 20] * (len(kernels) * len(repeats) + 1)))
    for key in interpreters:
        print(key.rjust(20), end=" ")
        for kname in kernels:
            for name in repeats:
                print(u'%20s' % results[name][key][kname][0], end=" ")
        print("")
    print(*(["=" * 20] * (len(kernels) * len(repeats) + 1)))
    print('\n\n\n')

if __name__ == "__main__":
    main()
