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
from setuptools import setup, find_packages

repo_base = os.path.abspath(os.path.dirname(__file__))

# Get package intro
long_description = []
with open(os.path.join(repo_base, 'cpy2py', '__init__.py')) as package_main:
    skip_header = True
    for line in (ln.strip() for ln in package_main):
        if line == '"""':  # start of docstring
            skip_header = False
            continue
        if "end_long_description" in line:
            break
        if not skip_header:
            long_description.append(line)
long_description = '\n'.join(long_description)

setup(
    name='cpy2py',

    # meta data
    version='0.9.0',

    description='Framework for combining different python interpeters',
    long_description=long_description,
    url='https://github.com/maxfischer2781/cpy2py',

    author='Max Fischer',
    author_email='maxfischer2781@gmail.com',

    license='Apache V2.0',
    platforms=['Operating System :: OS Independent'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        # TODO: confirm others
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Interpreters',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='interpreter framework development ipc processing pypy cpython',

    # content
    packages=find_packages(exclude=('cpy2py_*', 'dev_tools')),

    # unit tests
    test_suite='cpy2py_unittests'
)