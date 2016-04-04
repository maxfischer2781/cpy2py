#!/usr/bin/python
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
import matplotlib.pyplot as plt
import argparse
import sys
import json

from cpy2py import TwinMaster
import example_module

CLI = argparse.ArgumentParser()
CLI.add_argument(
    'callable',
    nargs='?',
    help='callable to benchmark. [default: %(default)s]',
    default='example_module.compute',
    const='example_module.compute',
)
CLI.add_argument(
    '-r',
    '--repetitions',
    type=int,
    help='Repetitions per power. [default: %(default)s]',
    default=4,
)
CLI.add_argument(
    '-p',
    '--power',
    type=int,
    help='Maximum power of problem size. [default: %(default)s]',
    default=6,
)
CLI.add_argument(
    '-b',
    '--base',
    type=int,
    help='Base of problem size. [default: %(default)s]',
    default=10,
)
CLI.add_argument(
    '-j',
    '--json',
    nargs='?',
    help='Save results as JSON. [default: %(default)s]',
    const='%(callable_name)s.json',
)
OPTIONS = CLI.parse_args()


def get_callable(callable_string):
    """
    Load a callable based on <module>.<name>

    :param callable_string: callable name of the form <module>.<name>
    :type callable_string: str
    """
    call_module, _, call_name = callable_string.rpartition('.')
    if not call_module:
        raise ValueError("callable must reside in module/package. Expected '<package>.<callable>'")
    __import__(call_module)
    try:
        return getattr(sys.modules[call_module], call_name)
    except AttributeError:
        raise ValueError("no callable '%s' in module '%s'" % (call_name, call_module))


def get_time(call_result):
    """Extract timing information from nested timing call"""
    tot_tme, call_result = call_result
    call_tme, _ = call_result
    return tot_tme, call_tme, tot_tme - call_tme


def fmt_time(call_result):
    """Format timing information from nested timing call"""
    return '%7.5f %7.5f %7.5f' % get_time(call_result)


TME_HEADER = ['total', 'call', 'delta']
FMT_HEADER = "TOTAL__ CALL___ DELTA__"

TIMING = {}  # {func => size => interpreter => tme => [rep]}


def start_twinterpeter():
    """Initialize and start a twinterpeter"""
    print("starting twinterpeter")
    twinterpreter = TwinMaster('pypy')
    twinterpreter.start()
    time.sleep(1)
    return twinterpreter


def time_callable(twinterpreter, func, scale):
    """Measure execution time natively and in twinterpeter"""
    master_result = example_module.time_call(
        example_module.time_call,
        func,
        scale
    )
    twin_result = example_module.time_call(
        twinterpreter.execute,
        example_module.time_call,
        func,
        scale
    )
    return master_result, twin_result


def store_results(master_result, twin_result, scale, func_name):
    """Store results of execution time measurement"""
    if scale not in TIMING[func_name]:
        TIMING[func_name][scale] = {}
        for interpreter in ('master', 'twin'):
            TIMING[func_name][scale][interpreter] = {
                header: []
                for header in TME_HEADER
                }
    tme_result = get_time(master_result)
    for idx, header in enumerate(TME_HEADER):
        TIMING[func_name][scale]['master'][header].append(tme_result[idx])
    tme_result = get_time(twin_result)
    for idx, header in enumerate(TME_HEADER):
        TIMING[func_name][scale]['twin'][header].append(tme_result[idx])


def print_results(master_result, twin_result, reps, power, func_name):
    """Print the current timing results"""
    print("\r" + ' ' * 120, end='')
    print("\r", func_name, '(%03d/%03d @ %02d**%02d)' % (
        reps, OPTIONS.repetitions, OPTIONS.base, power), end='')
    print("norm", fmt_time(master_result), end='')
    print("twin", fmt_time(twin_result), end='')


def dump_json():
    """Write results as json"""
    if OPTIONS.json is not None:
        json_fmt = {'callable_name': '_'.join(TIMING)}
        json_path = OPTIONS.json % json_fmt
        print("Writing benchmark to", json_path)
        with open(json_path, "w") as json_file:
            json.dump(TIMING, json_file)


def main():
    twinterpreter = start_twinterpeter()
    callables = (get_callable(OPTIONS.callable),)
    try:
        for rep in xrange(OPTIONS.repetitions):
            for func in callables:
                TIMING.setdefault(func.__name__, {})
                for power in xrange(OPTIONS.power):
                    scale = 1 * pow(OPTIONS.base, power)
                    master_result, twin_result = time_callable(twinterpreter, func, scale)
                    print_results(master_result, twin_result, rep, power, func.__name__)
                    store_results(master_result, twin_result, scale, func.__name__)
    except KeyboardInterrupt:
        if not TIMING:
            raise
        print("... KeyboardInterrupt")
    else:
        print("...")
    print("benchmarking done")

    # json
    dump_json()

    # plotting
    _, axes = plt.subplots(
        nrows=len(TIMING) * 3,
        ncols=len(TME_HEADER),
        figsize=(8, 6),
        gridspec_kw=dict(wspace=0.3, hspace=0.3)
    )
    for ridx, func_name in enumerate(TIMING):
        for cidx, tme_head in enumerate(TME_HEADER):
            # per call, sliced by power
            # absolute
            this_axes = axes[ridx * 3][cidx]
            max_scale_pow = math.log(max(TIMING[func_name]), 10) / 255.0
            this_axes.set_title('%s %s (slice)' % (func_name, tme_head))
            this_axes.set_yscale(value='log')
            this_axes.axhline(y=0.000001, linestyle='--')  # clock granularity
            for scale in TIMING[func_name]:
                this_axes.plot(
                    TIMING[func_name][scale]['master'][tme_head],
                    color="#FF00%02X" % (math.log(scale, 10) / max_scale_pow),
                )
                this_axes.plot(
                    TIMING[func_name][scale]['twin'][tme_head],
                    color="#00FF%02X" % (math.log(scale, 10) / max_scale_pow),
                )
            # per power
            # absolute
            this_axes = axes[ridx * 3 + 1][cidx]
            this_axes.set_title('%s %s (min/max/avg)' % (func_name, tme_head))
            this_axes.set_xscale(value='log')
            this_axes.set_yscale(value='log')
            this_axes.axhline(y=0.000001, linestyle='--')  # clock granularity
            x_all = sorted(TIMING[func_name])
            y_master = [
                sum(TIMING[func_name][scale]['master'][tme_head]) / len(TIMING[func_name][scale]['master'][tme_head])
                for scale in x_all
                ]
            y_master_min = [
                min(TIMING[func_name][scale]['master'][tme_head])
                for scale in x_all
                ]
            y_master_max = [
                max(TIMING[func_name][scale]['master'][tme_head])
                for scale in x_all
                ]
            y_twin = [
                sum(TIMING[func_name][scale]['twin'][tme_head]) / len(TIMING[func_name][scale]['twin'][tme_head])
                for scale in x_all
                ]
            y_twin_min = [
                min(TIMING[func_name][scale]['twin'][tme_head])
                for scale in x_all
                ]
            y_twin_max = [
                max(TIMING[func_name][scale]['twin'][tme_head])
                for scale in x_all
                ]
            # min/max
            this_axes.fill_between(
                x=sorted(TIMING[func_name]),
                y1=y_master_min,
                y2=y_master_max,
                color="#FF0000",
                alpha=0.2,
            )
            this_axes.fill_between(
                x=sorted(TIMING[func_name]),
                y1=y_twin_min,
                y2=y_twin_max,
                color="#00FF00",
                alpha=0.2,
            )
            # avg
            this_axes.errorbar(
                x=sorted(TIMING[func_name]),
                y=y_master,
                color="#FF0000",
            )
            this_axes.errorbar(
                x=sorted(TIMING[func_name]),
                y=y_twin,
                color="#00FF00",
            )
            # relative
            this_axes = axes[ridx * 3 + 2][cidx]
            this_axes.set_title('%s %s (relative)' % (func_name, tme_head))
            this_axes.axhline(y=1, linestyle='--')
            this_axes.set_xscale(value='log')
            this_axes.set_yscale(value='log')
            ratios = [
                (y_twin[tidx] / y_master[tidx], x_all[tidx])
                for tidx
                in xrange(len(x_all))
                if y_master[tidx] != 0
                ]
            x_ratio_min_max = [
                tidx
                for tidx
                in xrange(len(x_all))
                if y_master_min[tidx] != 0 and y_master_max[tidx] != 0
                ]
            ratios_min = [
                y_twin_min[tidx] / y_master_min[tidx]
                for tidx
                in x_ratio_min_max
                ]
            ratios_max = [
                y_twin_max[tidx] / y_master_max[tidx]
                for tidx
                in x_ratio_min_max
                ]
            this_axes.fill_between(
                x=[x_all[t_idx] for t_idx in x_ratio_min_max],
                y1=ratios_min,
                y2=ratios_max,
                color="#FFFF00",
                alpha=0.2,
            )
            this_axes.errorbar(
                x=[ratio[1] for ratio in ratios],
                y=[ratio[0] for ratio in ratios],
                color="#FFFF00",
            )
    plt.show()

if __name__ == "__main__":
    main()
