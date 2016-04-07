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
import time

from cpy2py.utility.compat import rangex


def time_call(call, *args, **kwargs):
    stime = time.time()
    result = call(*args, **kwargs)
    timing = time.time() - stime
    return timing, result


def square(arg):
    return arg * arg


def compute(size):
    value = 1.5
    for _ in rangex(size):
        value *= value
        value %= 9999.9
    return value


def powerize(size):
    value = 1.1
    for _ in rangex(size):
        value *= value
    return value


def adder(size):
    value = 1.1
    for _ in rangex(size):
        value += 1.1
    return value


def lots(size):
    value = 1.1
    for _ in rangex(size):
        value *= value
        value += value
        value %= 10000
    return value


def lots_const(size):
    value = 1.1
    for _ in rangex(size):
        value *= 1.1
        value += 1.1
        value %= 10000
    return value
