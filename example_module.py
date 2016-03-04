import time


def time_call(call, *args, **kwargs):
	stime = time.time()
	result = call(*args, **kwargs)
	timing = time.time() - stime
	return timing, result


def square(arg):
	return arg*arg


def compute(size):
	value = 1.5
	for _ in xrange(size):
		value *= value
		value %= 9999.9
	return value


def powerize(size):
	value = 1.1
	for _ in xrange(size):
		value *= value
	return value


def adder(size):
	value = 1.1
	for _ in xrange(size):
		value += 1.1
	return value
