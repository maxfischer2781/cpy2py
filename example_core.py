#!/usr/bin/python
# - # Copyright 2016 Max Fischer
# - #
# - # Licensed under the Apache License, Version 2.0 (the "License");
# - # you may not use this file except in compliance with the License.
# - # You may obtain a copy of the License at
# - #
# - # 	http://www.apache.org/licenses/LICENSE-2.0
# - #
# - # Unless required by applicable law or agreed to in writing, software
# - # distributed under the License is distributed on an "AS IS" BASIS,
# - # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# - # See the License for the specific language governing permissions and
# - # limitations under the License.
import cpy2py.twinterpreter.twin_pypy
import time
import math
import matplotlib.pyplot as plt

import example_module


def get_time(call_result):
	tot_tme, call_result = call_result
	call_tme, other = call_result
	return tot_tme, call_tme, tot_tme-call_tme


def fmt_time(call_result):
	return '%7.5f %7.5f %7.5f' % get_time(call_result)

tme_header = ['total', 'call', 'delta']
fmt_header = "TOTAL__ CALL___ DELTA__"

timing = {}  # {func => size => interpreter => tme => [rep]}

if __name__ == "__main__":
	print "starting"
	twinterpreter = cpy2py.twinterpreter.twin_pypy.TwinPyPy()
	twinterpreter.start()
	time.sleep(1)
	try:
		for rep in xrange(2):
			for func in (example_module.square, example_module.compute): #, example_module.adder, example_module.powerize):
				timing.setdefault(func.__name__, {})
				print "#############"
				print func.__name__, '(%03d)' % rep
				print 'V', fmt_header
				for power in xrange(2):
					scale = 1 * pow(10, power)
					if scale not in timing[func.__name__]:
						timing[func.__name__][scale] = {}
						for interpreter in ('master', 'twin'):
							timing[func.__name__][scale][interpreter] = {
								header: []
								for header in tme_header
							}
					print ">> count >>", scale
					result = example_module.time_call(
							example_module.time_call,
							func,
							scale
						)
					print "n", fmt_time(result)
					tme_result = get_time(result)
					for idx, header in enumerate(tme_header):
						timing[func.__name__][scale]['master'][header].append(tme_result[idx])
					result = example_module.time_call(
							twinterpreter.execute,
							example_module.time_call,
							func,
							scale
						)
					print "t", fmt_time(result)
					tme_result = get_time(result)
					for idx, header in enumerate(tme_header):
						timing[func.__name__][scale]['twin'][header].append(tme_result[idx])
	except KeyboardInterrupt:
		if not timing:
			raise
	print "done"

fig, axes = plt.subplots(nrows=len(timing), ncols=len(tme_header)*2, figsize=(8, 6))

for ridx, func_name in enumerate(timing):
	for cidx, tme_head in enumerate(tme_header):
		max_scale_pow = math.log(max(timing[func_name]), 10) / 255.0
		axes[ridx][cidx].set_title('%s %s (sliced)' % (func_name, tme_head))
		axes[ridx][cidx].set_yscale(value='log')
		for scale in timing[func_name]:
			axes[ridx][cidx].plot(
				timing[func_name][scale]['master'][tme_head],
				color="#FF00%02X" % (math.log(scale, 10) / max_scale_pow),
			)
			axes[ridx][cidx].plot(
				timing[func_name][scale]['twin'][tme_head],
				color="#00FF%02X" % (math.log(scale, 10) / max_scale_pow),
			)
		axes[ridx][len(tme_header)+cidx].set_title('%s %s' % (func_name, tme_head))
		axes[ridx][len(tme_header)+cidx].set_xscale(value='log')
		axes[ridx][len(tme_header)+cidx].set_yscale(value='log')
		axes[ridx][len(tme_header)+cidx].errorbar(
			x=sorted(timing[func_name]),
			y=[
				sum(timing[func_name][scale]['master'][tme_head]) / len(timing[func_name][scale]['master'][tme_head])
				for scale in sorted(timing[func_name])
			],
			color="#FF0000",
		)
		axes[ridx][len(tme_header)+cidx].errorbar(
			x=sorted(timing[func_name]),
			y=[
				sum(timing[func_name][scale]['twin'][tme_head]) / len(timing[func_name][scale]['twin'][tme_head])
				for scale in sorted(timing[func_name])
			],
			color="#00FF00",
		)
plt.show()
