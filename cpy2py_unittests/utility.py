"""
Utilities for running unittests
"""
from __future__ import print_function
import os
import errno
import tempfile
import subprocess
import atexit
import shutil
import time
import sys

import cpy2py
from cpy2py.twinterpreter import master
from cpy2py.twinterpreter import interpreter
from cpy2py.utility.compat import stringabc


class TestEnvironment(cpy2py.TwinObject):
    """
    Class for creating and storing the environment for tests

    :note: This object must derive from :py:class:`~cpy2py.TwinObject`
           to hold the same state in all twinterpreters. At least one
           basic test of :py:class:`~cpy2py.TwinObject` should not
           require such an environment.
    """
    def __init__(self, autostart=False):
        self.workdir_base = tempfile.mkdtemp()
        atexit.register(self.destroy_env)
        self.twin_masters = {}
        self.autostart = autostart

    def add_venv_master(self, executable=None, twinterpreter_id=None, kernel=None, requirements=None):
        """
        Add a python virtual environment and twin master

        :param executable: see :py:class:`~cpy2py.twinterpreter.twin_master.TwinProcess`
        :param twinterpreter_id: see :py:class:`~cpy2py.twinterpreter.twin_master.TwinProcess`
        :param requirements: package to install; :py:mod:`~cpy2py` is always added as the current version
        :type requirements: None or list[str]
        :return:
        """
        _interpreter = interpreter.Interpreter(executable or twinterpreter_id)
        _twinterpreter_id = twinterpreter_id or os.path.basename(_interpreter.executable)
        assert _twinterpreter_id not in self.twin_masters, "Collision in twinterpreter ids"
        print('creating virtualenv:', _interpreter, 'requires:', requirements, file=sys.stderr)
        # create virtual environment
        venv_dir = self._get_venv_dir(_twinterpreter_id)
        subprocess.check_call([
            'virtualenv',
            '--no-site-packages',
            '-p', _interpreter.executable,
            venv_dir,
        ])
        # add requirements
        pip_requirements = [
            os.path.dirname(os.path.dirname(os.path.abspath(cpy2py.__file__))),
            'coverage', 'unittest2'
        ]
        if isinstance(requirements, stringabc):
            pip_requirements.append(requirements)
        elif requirements is not None:
            pip_requirements.extend(requirements)
        for requirement in pip_requirements:
            subprocess.check_call([
                os.path.join(venv_dir, 'bin', 'pip'),
                'install', requirement,
                '--upgrade',
            ])
        # setup twin master
        self.twin_masters[_twinterpreter_id] = master.TwinMaster(
            executable=os.path.join(venv_dir, 'bin', 'python'),
            twinterpreter_id=_twinterpreter_id,
            kernel=kernel,
        )
        atexit.register(self.twin_masters[_twinterpreter_id].stop)
        if self.autostart:
            self.twin_masters[_twinterpreter_id].start()
        return self.twin_masters[_twinterpreter_id]

    def _get_venv_dir(self, twinterpreter_id):
        venv_dir = os.path.join(self.workdir_base, 'venv', twinterpreter_id)
        try:
            os.makedirs(venv_dir)
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
        return venv_dir

    def start_env(self):
        for master in self.twin_masters.values():
            master.start()

    def stop_env(self):
        for master in self.twin_masters.values():
            master.stop()

    def destroy_env(self, sleep=time.sleep, rmtree=shutil.rmtree):
        for key in list(self.twin_masters.keys()):
            self.twin_masters.pop(key).destroy()
        sleep(0.1)
        try:
            rmtree(self.workdir_base)
        except OSError:
            pass
