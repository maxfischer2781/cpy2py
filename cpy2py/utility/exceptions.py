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
import sys
import linecache


class CPy2PyException(Exception):
    """Base class for all custom exceptions"""
    pass


def format_namespace(logger, namespace, namespace_name):
    """
    Format information from a namespace dict

    :param logger: a :py:class:`~logging.Logger` to write to
    :type logger: :py:class:`~logging.Logger`
    :param namespace: namespace to format
    :type namespace: :py:class:`dict`
    :param namespace_name: name to identify namespace with
    :type namespace_name: str
    """
    logger.critical('    Namespace %s', namespace_name)
    if not namespace:
        logger.critical('      <empty>')
        return
    maxlen = max(len(var_name) for var_name in namespace)
    for var_name in sorted(namespace):
        logger.critical('      %s = %s', var_name.ljust(maxlen), format_repr(namespace[var_name]))


def format_repr(obj, max_len=120):
    """
    Return the representation of an object for display

    :param obj: any object to represent
    :param max_len: maximum length of representation
    :type max_len: int
    :return: formatted object representation
    """
    obj_repr = repr(obj)
    if len(obj_repr) > max_len:
        return obj_repr[:max_len - 3] + '...'
    return obj_repr


def format_line(line_no, current_file):
    """Get source file line, formatted for printing"""
    return '%4d%s' % (line_no, linecache.getline(current_file, line_no).rstrip().replace('\t', '  '))


def format_exception(logger, variable_depth=float('inf')):
    """
    Write the current stacktrace to a logger

    :param logger: a :py:class:`~logging.Logger` to write to
    :type logger: :py:class:`~logging.Logger`
    :param variable_depth: maximum depth of tracebacks to include full namespace
    :type variable_depth: int, float
    """
    exception_type, exception, traceback = sys.exc_info()
    logger.critical('_' * 120)
    exc_header = '%s: %s' % (exception_type.__name__, exception)
    logger.critical('%s%s', exc_header, 'Traceback (most recent call last)'.rjust(120 - len(exc_header)))
    tracebacks = []
    while traceback is not None:
        tracebacks.append(traceback)
        traceback = traceback.tb_next
    trace_depth = len(tracebacks)
    for traceback in tracebacks:
        if traceback is None:
            logger.critical('%02d/%02d <no traceback information>', trace_depth, len(tracebacks))
            continue
        current_file = traceback.tb_frame.f_code.co_filename
        current_call = traceback.tb_frame.f_code.co_name
        current_line = traceback.tb_lineno
        linecache.checkcache(current_file)
        # log position and code
        logger.critical('%02d/%02d "%s" (%s[%d])', trace_depth, len(tracebacks), current_call, current_file,
                        current_line)
        logger.critical('    %s', format_line(current_line - 1, current_file))
        logger.critical('--> %s', format_line(current_line, current_file))
        logger.critical('    %s', format_line(current_line + 1, current_file))
        # log current variables
        if trace_depth <= variable_depth:
            local_vars = dict(traceback.tb_frame.f_locals)
            local_class = local_vars.get('self')
            format_namespace(logger, local_vars, 'local')
            if local_class is not None:
                class_vars = getattr(local_class, '__dict__',
                                     getattr(local_class, '__slots__', getattr(local_class, '_fields', None)))
                format_namespace(logger, class_vars, 'self (%s)' % type(local_class))
        logger.critical('')
        trace_depth -= 1
    del traceback
    logger.critical(exc_header)
