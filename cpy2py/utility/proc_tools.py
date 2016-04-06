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
import os
import errno


def is_executable(path):
    """Test whether `path` points to an executable"""
    return os.access(path, os.X_OK)


def get_executable_path(command):
    """
    Lookup the path to `command`

    :param command: name or path of command
    :type command: str
    :return: path of executable for command
    :raises: OSError if no executable is found
    """
    # explicit path
    if os.path.dirname(command):
        if not os.path.exists(command):
            raise OSError(errno.ENOENT, 'No such file or directory')
        if is_executable(command):
            return command
        else:
            raise OSError(errno.EACCES, 'Permission denied')
    # windows default command extensions
    path_exts = os.environ.get('PATHEXT', '').split(os.pathsep)
    # path lookup
    for path_dir in os.environ.get('PATH', '').split(os.pathsep):
        exe_path = os.path.join(path_dir, command)
        for path_ext in path_exts:
            if is_executable(exe_path + path_ext):
                return exe_path + path_ext
    raise OSError(errno.ENOENT, 'No such file or directory')



