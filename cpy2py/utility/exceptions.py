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
import sys
import linecache

class CPy2PyException(Exception):
	"""Base class for all custom exceptions"""
	pass


def format_namespace(logger, namespace, namespace_name):
	logger.critical('   Namespace %s', namespace_name)
	if not namespace:
		logger.critical('     <none>')
		return
	maxlen = max(len(var_name) for var_name in namespace)
	for var_name in sorted(namespace):
		logger.critical('     %s = %s', var_name.ljust(maxlen), format_repr(namespace[var_name]))


def format_repr(obj, max_len=120):
	try:
		obj_repr = repr(obj)
		if len(obj_repr) > max_len:
			return obj_repr[:max_len-3] + '...'
		return obj_repr
	except Exception:
		return '<not representable>'


def format_exception(logger, variable_depth=1):
	exception_type, exception, traceback = sys.exc_info()
	logger.critical('  %s: %s', exception.__class__.__name__, exception)
	tracebacks = []
	while traceback is not None:
		traceback = traceback.tb_next
		tracebacks.append(traceback)
	trace_depth = len(tracebacks)
	for traceback in tracebacks:
		if traceback is None:
			logger.critical('-+-%02d/%02d <no frame information>', trace_depth, len(tracebacks))
			continue
		current_file = traceback.tb_frame.f_code.co_filename
		current_call = traceback.tb_frame.f_code.co_name
		current_line = traceback.tb_lineno
		linecache.checkcache(current_file)
		format_line = lambda line_no: linecache.getline(current_file, line_no).rstrip().replace('\t', '  ')
		# log position and code
		logger.critical('-+-%02d/%02d "%s" (%s[%d])', trace_depth, len(tracebacks), current_call, current_file, current_line)
		logger.critical(' \>%s', format_line(current_line))
		# log current variables
		if trace_depth <= variable_depth:
			local_vars = dict(traceback.tb_frame.f_locals)
			local_class = local_vars.get('self', None)
			format_namespace(logger, local_vars, 'local')
			if local_class is not None:
				class_vars = getattr(local_class, '__dict__', getattr(local_class, '__slots__', getattr(local_class, '_fields', None)))
				format_namespace(logger, class_vars, 'self (%s)' % type(local_class))
		trace_depth -= 1
	del traceback
	logger.critical('  %s: %s', exception.__class__.__name__, exception)
