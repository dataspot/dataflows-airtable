# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import io
from setuptools import setup, find_packages


# Helpers
def read(*paths):
    """Read a text file."""
    basedir = os.path.dirname(__file__)
    fullpath = os.path.join(basedir, *paths)
    contents = io.open(fullpath, encoding='utf-8').read().strip()
    return contents


# Prepare
PACKAGE = 'dataflows_airtable'
NAME = PACKAGE.replace('_', '-')
INSTALL_REQUIRES = [
    'six',
    'dataflows',
]
TESTS_REQUIRE = [
    'moto[server]',
    'pytest-cov',
    'pytest',
    'pylama',
    'mock',
    'tox',
]
README = read('README.md')
VERSION = read(PACKAGE, 'VERSION')
PACKAGES = find_packages(exclude=['examples', 'tests'])


# Run
setup(
    name=NAME,
    version=VERSION,
    packages=PACKAGES,
    include_package_data=True,
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    extras_require={'develop': TESTS_REQUIRE},
    zip_safe=False,
    long_description=README,
    long_description_content_type="text/markdown",
    description='Python library for adding AirTable support to dataflows',
    author='Adam Kariv',
    author_email='adam.kariv@gmail.com',
    url='https://github.com/dataspot/dataflows-airtable',
    license='MIT',
    keywords=[
        'frictionless data',
        'open data',
        'airtable',
        'dataflows',
        'table schema',
        'data package',
        'tabular data package',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
