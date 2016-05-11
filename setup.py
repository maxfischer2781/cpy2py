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
import re
import sys
import codecs
from setuptools import setup, find_packages

# guard against rerunning setup.py when bootstrapping __main__
if __name__ == '__main__':
    repo_base = os.path.abspath(os.path.dirname(__file__))

    # grab meta without import package
    sys.path.insert(0, os.path.join(repo_base, 'cpy2py'))
    import meta as cpy2py_meta

    install_requires = []
    try:
        import argparse
    except ImportError:
        install_requires.append('argparse')

    # use readme for long descripion
    with codecs.open(os.path.join(repo_base, 'README.rst'), encoding='utf-8') as f:
        long_description = f.read()
    for directive_re, replacement_re in [
        (':py:\S*?:`~(.*?)`', '`\g<1>`'),
        (':py:\S*?:', ''),
        (':envvar:', ''),
    ]:
        long_description = re.sub(directive_re, replacement_re, long_description)

    if '--longdescription' in sys.argv:
        print(long_description)
        sys.exit(1)

    setup(
        name='cpy2py',

        # meta data
        version=cpy2py_meta.__version__,

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
            # TODO: confirm others
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
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
        install_requires=install_requires,
        extras_require={
            'example': ['matplotlib'],
            'profiling': ['vmprof'],
            'coverage': ['coverage'],
        },
        # unit tests
        test_suite='cpy2py_unittests',
    )
