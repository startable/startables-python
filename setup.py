#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the version number from version.py
version = {}
with open(path.join(here, 'version.py')) as fp:
    exec(fp.read(), version)

setup(
    name='startables',
    version=version['__version__'],
    description='Reads, writes, and manipulates data stored in StarTable format',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/startable/startables-python/',
    author='Jean-François Corbett',
    author_email='jeaco@orsted.dk',
    license='BSD-3-Clause',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD-3-Clause',
        'Programming Language :: Python :: 3',
    ],

    # What does your project relate to?
    keywords='startable data-structure file-format table',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests', 'test']),

    python_requires='>=3.6',

    install_requires=['numpy', 'pandas', 'openpyxl'],

    # Same for developer dependencies
    # extras_require={
    #     'dev': ['check-manifest'],
    #     'test': ['coverage'],
    # },

)
