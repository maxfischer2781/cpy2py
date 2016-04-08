"""
Configuration interface for debug mechanisms.

:warning: This module is intended to enable/disable features
          which ease debugging. Interfaces and features may
          change or be removed at any time.

.. envvar:: CPY2PY_DEBUG

  Log debug information to `stderr`.

.. envvar:: CPY2PY_AUTOTWIN

  Automatically start twinterpreters when creating :py:class:`~.TwinObject` instances.
"""
import logging as _logging
import os as _os

from cpy2py.utility.compat import NullHandler


def set_logging():
    """Set default logging"""
    _base_logger = _logging.getLogger('__cpy2py__')
    _base_logger.propagate = False
    # debugging logger to stderr
    if _os.environ.get('CPY2PY_DEBUG'):
        _base_logger.addHandler(_logging.StreamHandler())
    else:
        _base_logger.addHandler(NullHandler())


def set_autostart():
    """Set twinterpreter autostarting"""
    _base_logger = _logging.getLogger('__cpy2py__')
    _base_logger.propagate = False
    # debugging logger to stderr
    if _os.environ.get('CPY2PY_AUTOTWIN'):
        _base_logger.addHandler(_logging.StreamHandler())
    else:
        _base_logger.addHandler(NullHandler())


def configure():
    """Configure optionals of :py:mod:`cpy2py`"""
    set_logging()
    set_autostart()
