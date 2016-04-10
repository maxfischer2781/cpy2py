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
from __future__ import print_function
import argparse
import os
import re
import subprocess

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
CLI.add_argument(
    "-t",
    "--tag-message",
    help="Message for an annotated git tag. Required for minor and major version bumps.",
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
        return [version[0], (version[1] + 1), 0]
    elif target == 'major':
        return [(version[0] + 1), 0, 0]
    raise ValueError


def write_version(version_file, new_version):
    """Update the version file with a new version number"""
    version_file_tmp = version_file + '.vtp'
    with open(version_file, 'r') as in_file, open(version_file_tmp, 'w') as out_file:
        for line in in_file:
            if re.match(VERSION_STR_RE, line):
                line_remainder = re.match(VERSION_STR_RE, line).group(2)
                line = '__version__ = "%s"%s\n' % (format_version(new_version), line_remainder)
            out_file.write(line)
    # rename when done writing
    stat = os.stat(version_file)
    os.chmod(version_file_tmp, stat.st_mode)
    os.chown(version_file_tmp, stat.st_uid, stat.st_gid)
    os.rename(version_file_tmp, version_file)


def make_commit(version_file, new_version, message=None):
    commit_message = 'v' + format_version(new_version)
    if message:
        commit_message += '\n' + message
    # make sure version is committed
    subprocess.check_call([
        'git', 'reset', 'HEAD'
    ])
    subprocess.check_call([
        'git', 'add', version_file
    ])
    # make commit
    subprocess.check_call([
        'git', 'commit', '-m', commit_message
    ])


def make_version_tag_commit(new_version, message):
    tag = 'v' + format_version(new_version)
    subprocess.check_call([
        'git', 'tag',
        '-a', tag,
        '-m', message
    ])
    return tag


def main():
    """Run the main update loop"""
    options = CLI.parse_args()
    version = read_version(options.version_file)
    print('current version:', format_version(version))
    if options.target is None:
        return
    if options.target in ('major', 'manior') and not options.tag_message:
        raise ValueError("Must specify a tag message when bumping minor or major version.")
    new_version = bump_version(version, options.target)
    write_version(options.version_file, new_version)
    print('updated version:', format_version(new_version))
    make_commit(options.version_file, new_version, options.tag_message)
    print('commited version')
    if options.tag_message:
        tag = make_version_tag_commit(new_version, options.tag_message)
        print('added tag:', tag)


if __name__ == "__main__":
    main()
