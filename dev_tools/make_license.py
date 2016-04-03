#!/usr/bin/python
# -*- coding: utf-8 -*-
# - # Copyright 2015 Karlsruhe Institute of Technology
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
"""
Add license information to repository
"""
from __future__ import print_function

import subprocess
import argparse
import collections
import datetime
import re
import os
import hashlib
import urllib2

from dev_tools.license_data import NOTICE_TEMPLATE, LICENSE_HEADER_TEMPLATE, PRIMARY_AUTHOR_LIST

# symbol sequence at the start of each license line, per file extension
LICENSE_START_SYMBOLS = {
    None: "# - # ",  # default
    ".py": "# - # ",
    ".rst": ".. # - #",
}
PRESERVE_LINES = [
    r"^#!",  # shebang
    r"coding[:=]\s*([-\w.]+)",  # python encoding line
]

# extension for temporary files
TEMP_EXTENSION = ".lsc.tmp"

REPO_BASE = os.path.realpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
)
SOURCE_FILE_RE = ".*.py$|.*.sh$|.*.rst$"

CLI = argparse.ArgumentParser(
    "Update licensing information of the project",
)
CLI.add_argument(
    "-r",
    "--repo-base",
    help="Basedir of repository. [default: %(default)s]",
    default=REPO_BASE,
)
CLI.add_argument(
    "-d",
    "--source-dirs",
    nargs="*",
    help="List of directories containing package source, relative to repo root. [default: %(default)s]",
    default=[
        repo_dir
        for repo_dir in
        os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
        if os.path.isdir(os.path.join(REPO_BASE, repo_dir)) and
        not any(
            re.search(exclude_repo_dir_re, repo_dir)
            for exclude_repo_dir_re in
            ['unittests', '^dev_tools$', '^[.]']
        )
    ],
)
CLI.add_argument(
    "-f",
    "--source-files",
    nargs="*",
    help="Individual files containing package source. [default: %(default)s]",
    default=[
        repo_file
        for repo_file in
        os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
        if
        os.path.isfile(os.path.join(REPO_BASE, repo_file)) and
        re.search(SOURCE_FILE_RE, os.path.join(REPO_BASE, repo_file)) and
        not any(
            re.search(exclude_repo_file_re, repo_file)
            for exclude_repo_file_re in
            ['^[.]', '^NOTICE$', '^README$']
        )
    ],
)
CLI.add_argument(
    "-l",
    "--fetch-license",
    nargs="?",
    help="Fetch license text. Optionally specify URL. [default: %(default)s]",
    const="http://www.apache.org/licenses/LICENSE-2.0",
)
CLI.add_argument(
    "-a",
    "--primary-author",
    nargs="*",
    help="Names of primary authors. [default: %(default)s]",
    default=PRIMARY_AUTHOR_LIST,
)
CLI.add_argument(
    "-n",
    "--update-notice",
    action="store_true",
    help="Add license notice. [default: %(default)s]",
)


def get_format_data(source_file=None):
    """
    Get license formatting data

    :param source_file: Optional file for which to extract information
    :return:
    """
    # repo url
    try:
        repo_url = subprocess.check_output(['git', 'config', 'remote.origin.url']).splitlines()[0]
    except subprocess.CalledProcessError as err:
        if err.returncode != 128 and err.returncode != 1:
            raise
        repo_url = ""
    # modification dates
    try:
        file_change_dates = subprocess.check_output(
            ['git', 'log', '--format=%ai'] + (['--follow', source_file] if source_file is not None else [])
        ).splitlines()
    except subprocess.CalledProcessError as err:
        if err.returncode != 128:
            raise
        file_change_dates = []
    if file_change_dates:
        first_year = file_change_dates[-1].split('-')[0]
        last_year = file_change_dates[0].split('-')[0]
        if first_year == last_year:
            dev_years = first_year
        else:
            dev_years = first_year + '-' + last_year
    else:
        dev_years = datetime.date.today().year
    # repo contributors
    contributors_list = []
    for contributor in get_contributors(source_file=source_file):
        if contributor.name == 'Total':
            continue
        contributors_list.append(contributor)
    return {
        "package_name": os.path.dirname(REPO_BASE),
        "dev_years": dev_years,
        "primary_authors": ', '.join(PRIMARY_AUTHOR_LIST),
        "contributors": ', '.join(contributor.name for contributor in contributors_list),
        "contributor_listing": '\n'.join(contributor.contact for contributor in contributors_list),
        "repo_url": repo_url,
    }


def update_file(old_file, new_file, comparebytes=float("inf")):
    """
    Replaces `old_file` with `new_file`

    This function ensures that the path `old_file` will include the content of
    `new_file` and that `new_file` will no longer exist. If the files have the
    same content, `new_file` will simply be deleted.

    :param old_file: path to old file
    :type old_file: str
    :param new_file: path to new file
    :type new_file: str
    :param comparebytes: maximum number of bytes to compare
    :type comparebytes: int or float
    :return: whether `old_file` has changed
    :rtype: bool
    """
    if not os.path.isfile(old_file):
        os.rename(new_file, old_file)
        return True
    if filehash(old_file, maxbytes=comparebytes) != filehash(new_file, maxbytes=comparebytes):
        print(old_file, "!=", new_file)
        stat = os.stat(old_file)
        os.chmod(new_file, stat.st_mode)
        os.chown(new_file, stat.st_uid, stat.st_gid)
        os.rename(new_file, old_file)
        return True
    print(old_file, "==", new_file)
    os.unlink(new_file)
    return False


def filehash(filepath, blocksize=65536, maxbytes=float("inf")):
    """
    Create the sha512 hash of a file's content or portion thereof

    :param filepath: path to file
    :type filepath: str
    :param blocksize: size of blocks read from file
    :type blocksize: int
    :param maxbytes: maximum number of bytes to compare
    :type maxbytes: int or float
    :return:
    """
    fhash = hashlib.sha512()
    with open(filepath, "rb") as filedata:
        bytesread, databuffer = 0, filedata.read(blocksize)
        while databuffer and bytesread < maxbytes:
            fhash.update(databuffer)
            bytesread += len(databuffer)
            databuffer = filedata.read(blocksize)
    return fhash.hexdigest()


def write_license(license_url, license_file):
    """Write license file"""
    try:
        license_data = urllib2.urlopen(license_url)
    except urllib2.URLError:
        print("Failed fetching LICENSE")
        return False
    license_tmp = license_file + TEMP_EXTENSION
    with open(license_tmp, 'wb') as output_file:
        output_file.write(license_data.read())
    return update_file(license_file, license_tmp)


def get_license_target_files(
        source_files, source_dirs,
):
    """
    Compile a list of all files that require licenses
    """
    # folders which include files subject to licensing
    for folder in source_dirs:
        for dirpath, _, filenames in os.walk(os.path.join(REPO_BASE, folder)):
            for filename in filenames:
                if re.search(SOURCE_FILE_RE, filename):
                    yield os.path.join(dirpath, filename)
    for filename in source_files:
        yield os.path.join(REPO_BASE, filename)


def update_license_header(filepath):
    """
    Update the license header for a specific file

    :param filepath: file to update with header
    :type filepath: str
    :return: whether the file has changed
    """
    license_header = LICENSE_HEADER_TEMPLATE % get_format_data(source_file=filepath)
    # insert license if applicable
    _, file_type = os.path.splitext(filepath)
    license_seq = LICENSE_START_SYMBOLS.get(file_type, LICENSE_START_SYMBOLS[None])
    done_insert = False
    filepath_tmp = filepath + TEMP_EXTENSION
    with open(filepath_tmp, 'w') as output_file, open(filepath) as input_file:
        # iterate lines, adding header directly AFTER shebang and encoding
        for source_line in input_file:
            if not done_insert:
                # always skip existing header, add a new one
                if source_line.startswith(license_seq.strip()):
                    continue
                # always preserve leading content
                elif any(re.search(preserve_re, source_line) for preserve_re in PRESERVE_LINES):
                    output_file.write(source_line)
                    continue
                # write header, continue with source
                else:
                    for header_line in license_header.splitlines():
                        if header_line:
                            output_file.write((license_seq + header_line) + "\n")
                        else:
                            output_file.write(license_seq.strip() + "\n")
                    done_insert = True
            output_file.write(source_line)
    # check content change
    return update_file(
        filepath,
        filepath_tmp,
        comparebytes=max(len(license_header), len(LICENSE_HEADER_TEMPLATE)) * 2
    )


class Contributor(object):
    """
    Contributor to a git repository

    :param name_str: raw name of the contributor
    :type name_str: str
    """
    contributors = {}

    def __new__(cls, name_str):
        unified_name = cls.unify_name(name_str)
        try:
            return cls.contributors[unified_name]
        except KeyError:
            contributor = object.__new__(cls, unified_name)
            cls.contributors[unified_name] = contributor
        return contributor

    def __init__(self, name_str):
        if hasattr(self, 'name'):
            return
        self.name = self.unify_name(name_str)
        self.emails = collections.Counter()
        self.commit_count = 0
        self.additions = 0
        self.deletions = 0
        self.files = set()

    @property
    def email(self):
        """Most used email address"""
        if not self.emails:
            return None
        return sorted(self.emails.iteritems(), key=lambda item: item[1])[-1][0]

    @property
    def contact(self):
        """Contact information"""
        return "%20s <%s>" % (self.name, ",".join(
            mail for mail, count in sorted(self.emails.iteritems(), key=lambda item: item[1], reverse=True)))

    def add_commit(self, email=None):
        """
        Add general data of a commit
        """
        self.commit_count += 1
        self.emails[email] += 1

    def add_diff(self, filepath, additions, deletions):
        self.additions += additions
        self.deletions += deletions
        self.files.add(filepath)

    def __str__(self):
        return "%20s, %5d commits, %5d files, %6d additions, %6d deletions, <%20s>" % (
            self.name,
            self.commit_count,
            len(self.files),
            self.additions,
            self.deletions,
            ",".join(mail for mail, count in sorted(self.emails.iteritems(), key=lambda item: item[1], reverse=True))
        )

    @staticmethod
    def unify_name(name_str):
        return " ".join([sub_name.capitalize() for sub_name in name_str.split()])


def get_contributors(aliases=None, source_file=None):
    """
    Get list of contributors weighted by lines of code

    :return:
    """
    aliases = {} if aliases is None else aliases
    try:
        changes = subprocess.check_output(
            ['git', 'log', '--format="%H|%aN|%aE"', '--no-merges', '-w', '--numstat'] + (
                ['--follow', source_file] if source_file is not None else [])
        ).splitlines()
    except subprocess.CalledProcessError as err:
        if err.returncode != 128:
            raise
        changes = []
    total = contributor = Contributor("Total")
    for change_line in changes:
        change_line = change_line.strip().strip('"')
        if not change_line:
            continue
        if '|' in change_line and '@' in change_line:
            _, author, email = change_line.split('|')
            contributor = Contributor(aliases.get(author, author))
            contributor.add_commit(email)
            total.add_commit(email)
        else:
            additions, deletions, filepath = change_line.split(None, 2)
            additions = 0 if additions == '-' else int(additions)
            deletions = 0 if deletions == '-' else int(deletions)
            contributor.add_diff(filepath, additions, deletions)
            total.add_diff(filepath, additions, deletions)
    for contributor in sorted(Contributor.contributors.values(), key=lambda con: con.commit_count):
        if contributor == total:
            continue
        yield contributor


def write_notice(notice_file):
    notice_data = NOTICE_TEMPLATE % get_format_data()
    notice_tmp = notice_file + TEMP_EXTENSION
    with open(notice_tmp, 'wb') as output_file:
        output_file.write(notice_data)
    return update_file(notice_file, notice_tmp)


def main():
    options = CLI.parse_args()
    if write_notice(notice_file=os.path.join(REPO_BASE, "NOTICE")):
        print("Added NOTICE")
    else:
        print("Skipped NOTICE")
    if options.fetch_license and write_license(license_url=options.fetch_license,
                                               license_file=os.path.join(REPO_BASE, "LICENSE")):
        print("Added LICENSE")
    else:
        print("Skipped LICENSE")
    print(list(get_license_target_files(source_files=options.source_files, source_dirs=options.source_dirs)))
    for file_path in get_license_target_files(source_files=options.source_files, source_dirs=options.source_dirs):
        print(file_path)
        update_license_header(file_path)


if __name__ == "__main__":
    main()
