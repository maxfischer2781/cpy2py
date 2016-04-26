"""
Utilities for running unittests
"""
import os
import errno
import tempfile
import subprocess
import atexit
import shutil
import time

import cpy2py
from cpy2py.twinterpreter import twin_master
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

    def add_venv_master(self, executable=None, twinterpreter_id=None, requirements=None):
        """
        Add a python virtual environment and twin master

        :param executable: see :py:class:`~cpy2py.twinterpreter.twin_master.TwinDef`
        :param twinterpreter_id: see :py:class:`~cpy2py.twinterpreter.twin_master.TwinDef`
        :param requirements: package to install; :py:mod:`~cpy2py` is always added as the current version
        :type requirements: None or list[str]
        :return:
        """
        parent_def = twin_master.TwinDef(executable, twinterpreter_id)
        assert parent_def.twinterpreter_id not in self.twin_masters, "Collision in twinterpreter ids"
        # create virtual environment
        venv_dir = self._get_venv_dir(parent_def.twinterpreter_id)
        subprocess.check_call([
            'virtualenv',
            '-p', parent_def.executable,
            venv_dir
        ])
        # add requirements
        pip_requirements = [os.path.dirname(os.path.dirname(os.path.abspath(cpy2py.__file__)))]
        if isinstance(requirements, stringabc):
            pip_requirements.append(requirements)
        elif requirements is not None:
            pip_requirements.extend(requirements)
        for requirement in pip_requirements:
            subprocess.check_call([
                os.path.join(venv_dir, 'bin', 'pip'),
                'install', requirement,
            ])
        # setup twin master
        self.twin_masters[parent_def.twinterpreter_id] = twin_master.TwinMaster(
            executable=os.path.join(venv_dir, 'bin', 'python'),
            twinterpreter_id=parent_def.twinterpreter_id
        )
        atexit.register(self.twin_masters[parent_def.twinterpreter_id].stop)
        if self.autostart:
            self.twin_masters[parent_def.twinterpreter_id].start()
        return self.twin_masters[parent_def.twinterpreter_id]

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
