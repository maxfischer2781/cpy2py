from __future__ import print_function
import argparse
import os
import re

REPO_BASE = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

CLI = argparse.ArgumentParser("Set the package version information")

CLI.add_argument(
    "target",
    help="The part of the current version to bump.",
    choices=('major', 'minor', 'patch', None),
    nargs='?',
    default=None,
)
CLI.add_argument(
    "-f",
    "--version-file",
    help="The file containing the __version__ field.",
    default=os.path.join(REPO_BASE, 'cpy2py', 'meta.py'),
)

VERSION_STR_RE = r'^__version__\s*=\s*"([0-9]+(?:[.][0-9]+(?:[.][0-9]+)))"(.*)$'


def read_version(version_file):
    """Read the current version number"""
    version_str = '0.0.0'
    with open(version_file, 'r') as vfile:
        for line in vfile:
            if re.match(VERSION_STR_RE, line):
                version_str = re.match(VERSION_STR_RE, line).group(1)
                break
        else:
            raise ValueError("No version information in '%s'" % version_file)
    if version_str.count('.') > 2:
        raise ValueError("Version string '%s' does not match <major>.<minor>.<patch> scheme" % version_str)
    return [int(mver) for mver in version_str.split('.')] + [0] * (2 - version_str.count('.'))


def format_version(version):
    """Create version str vom version tuple"""
    return '.'.join(str(mver) for mver in version)


def bump_version(version, target):
    """Bump the corresponding target part of bump_version"""
    if target is None:
        return version
    if target == 'patch':
        return version[:2] + [version[2] + 1]
    elif target == 'minor':
        return version[:1] + [version[1] + 1] + version[-1:]
    elif target == 'major':
        return [version[0] + 1] + version[-2:]
    raise ValueError


def write_version(version_file, new_version):
    """Update the version file with a new version number"""
    version_file_tmp = version_file + '.vtp'
    with open(version_file, 'r') as in_file, open(version_file_tmp, 'w') as out_file:
        for line in in_file:
            if re.match(VERSION_STR_RE, line):
                version_str, line_remainder = re.match(VERSION_STR_RE, line).groups()
                line = '__version__ = "%s"%s\n' % (format_version(new_version), line_remainder)
            out_file.write(line)
    # rename when done writing
    stat = os.stat(version_file)
    os.chmod(version_file_tmp, stat.st_mode)
    os.chown(version_file_tmp, stat.st_uid, stat.st_gid)
    os.rename(version_file_tmp, version_file)


def main():
    """Run the main update loop"""
    options = CLI.parse_args()
    version = read_version(options.version_file)
    print('current version:', format_version(version))
    if options.target is None:
        return
    new_version = bump_version(version, options.target)
    print('updated version:', format_version(new_version))
    write_version(options.version_file, new_version)

if __name__ == "__main__":
    main()
