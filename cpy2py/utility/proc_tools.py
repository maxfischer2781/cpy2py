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



