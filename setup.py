# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module for information retrieval."""

import os

from setuptools import find_packages, setup

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

tests_require = [
    'check-manifest>=0.35',
    'coverage>=4.0',
    'invenio-db[versioning]>=1.0.0',
    'isort>=4.2.15',
    'mock>=1.3.0',
    'pydocstyle>=1.0.0',
    'pytest-cov>=1.8.0',
    'pytest-random-order>=0.5.4',
    "pytest-pep8>=1.0.6",
    'pytest>=3.8.1,<4',
]

extras_require = {
    'docs': [
        'Sphinx>=1.5.6,<1.6',
        'invenio-accounts>=1.0.0',
    ],
    # Elasticsearch version
    'elasticsearch2': [
        'elasticsearch>=2.0.0,<3.0.0',
        'elasticsearch-dsl>=2.0.0,<3.0.0',
    ],
    'elasticsearch5': [
        'elasticsearch>=5.0.0,<6.0.0',
        'elasticsearch-dsl>=5.1.0,<6.0.0',
    ],
    'elasticsearch6': [
        'elasticsearch>=6.0.0,<7.0.0',
        'elasticsearch-dsl>=6.0.0,<6.2.0',
    ],
    'elasticsearch7': [
        'elasticsearch>=7.0.0,<8.0.0',
        'elasticsearch-dsl>=7.0.0,<8.0.0',
    ],
    'tests': tests_require,
}

extras_require['all'] = []
for name, reqs in extras_require.items():
    if name[0] == ':' or name in (
            'elasticsearch2', 'elasticsearch5', 'elasticsearch6',
            'elasticsearch7'):
        continue
    extras_require['all'].extend(reqs)


setup_requires = [
    'pytest-runner>=2.6.2',
]

install_requires = [
    'Flask>=0.11.1',
]

packages = find_packages()

# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('invenio_search', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='invenio-search',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='invenio search',
    license='MIT',
    author='CERN',
    author_email='info@inveniosoftware.org',
    url='https://github.com/inveniosoftware/invenio-search',
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    entry_points={
        'invenio_base.api_apps': [
            'invenio_search = invenio_search:InvenioSearch',
        ],
        'invenio_base.apps': [
            'invenio_search = invenio_search:InvenioSearch',
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Development Status :: 5 - Production/Stable',
    ],
)
