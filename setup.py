#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import ast
from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()


_version_re = re.compile(r'__version__\s+=\s+(.*)')


with open('rbchrome/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))


requirements = [
    'websocket-client==0.58.0',    
]

setup(
    name='rbchrome',
    version=version,
    description="A Python Package for the Google Chrome Dev Protocol",
    long_description=readme,
    author="anbuhckr",
    author_email='anbu.hckr@hotmail.com',
    url='https://github.com/anbuhckr/rbchrome',
    packages=find_packages(),
    package_dir={},    
    include_package_data=True,
    install_requires=requirements,
    license="GNU GENERAL PUBLIC LICENSE",
    zip_safe=False,
    keywords='rbchrome',
    classifiers=[
        'Development Status :: 4 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: BSD License',
        'Natural Language :: English',        
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Browsers'
    ],
)
