#!/usr/local/bin/python
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
r"""
Example for dispatching functions to specific interpreters

This example uses two functions, which are assigned to specific interpreters -
`pypy` and the default `python`. The `pypy` function is used to speed up a
nested loop of O(N\ :sup:2\ ) complexity. At the same time, the `python`
function uses the :py:mod:`matplotlib` module, which is not available in
other interpreters.
"""
from cpy2py import TwinMaster, twinfunction
import sys
import time
import math
import argparse


# loops in PyPy
@twinfunction('pypy')
def prime_sieve(max_val):
    start_time = time.time()
    primes = [1] * 2 + [0] * (max_val - 1)
    for value, factors in enumerate(primes):
        if factors == 0:
            for multiple in xrange(value*value, max_val + 1, value):
                primes[multiple] += 1
    return {'xy': [
        [primes[idx] == 0 for idx in range(minidx, minidx + int(math.sqrt(max_val)))]
        for minidx in range(0, max_val, int(math.sqrt(max_val)))
        ], 'info': '%s in %.1fs' % (sys.executable, time.time() - start_time)}


# matplotlib in CPython
@twinfunction('python')
def draw(xy, info='<None>'):
    from matplotlib import pyplot
    pyplot.copper()
    pyplot.matshow(xy)
    pyplot.xlabel(info, color="red")
    pyplot.show()

if __name__ == '__main__':
    CLI = argparse.ArgumentParser('function twin example')
    CLI.add_argument('COUNT', help='size of computation', type=int, default=int(1E6), nargs='?')
    options = CLI.parse_args()
    twins = [TwinMaster('python'), TwinMaster('pypy')]
    for twin in twins:
        twin.start()
    data = prime_sieve(options.COUNT)
    draw(**data)
