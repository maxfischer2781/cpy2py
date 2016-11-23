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
Dispatching functions to specific Twinterpreters
================================================

This example uses two functions, which are assigned to specific interpreters -
`pypy` and the default `python`. The `pypy` function is used to speed up a
nested loop of O(N\ :sup:`2`\ ) complexity. At the same time, the `python`
function uses the :py:mod:`matplotlib` module, which is not available in
other interpreters.
"""  # end intro
from cpy2py import TwinMaster, twinfunction
import sys
import time
import math


# extensive code run in PyPy for optimizations
@twinfunction('pypy')
def prime_sieve(max_val):
    """Sieve prime numbers"""
    start_time = time.time()
    primes = [1] * 2 + [0] * (max_val - 1)
    for value, factors in enumerate(primes):
        if factors == 0:
            for multiple in xrange(value * value, max_val + 1, value):
                primes[multiple] += 1
    return {
        'xy_matrix': [
            [primes[idx] == 0 for idx in range(minidx, minidx + int(math.sqrt(max_val)))]
            for minidx in range(0, max_val, int(math.sqrt(max_val)))
        ],
        'info': '%s in %.1fs' % (sys.executable, time.time() - start_time)
    }


# matplotlib in CPython
@twinfunction('python')
def draw(xy_matrix, info='<None>'):
    """Draw an XY matrix and attach some info"""
    from matplotlib import pyplot
    pyplot.copper()
    pyplot.matshow(xy_matrix)
    pyplot.xlabel(info, color="red")
    pyplot.show()


# native function not assigned to particular interpreter
def main():
    """Find and draw prime numbers"""
    import argparse
    cli = argparse.ArgumentParser('function twin example')
    cli.add_argument('COUNT', help='size of computation', type=int, default=int(1E6), nargs='?')
    options = cli.parse_args()
    # Twinterpreters must be started explicitly
    twins = [TwinMaster('python'), TwinMaster('pypy')]
    for twin in twins:
        twin.start()
    # twins can be chained directly
    draw(**prime_sieve(options.COUNT))


# protect main thread from executing again in other interpreters
if __name__ == '__main__':
    main()
