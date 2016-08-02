#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='rattle',
    version='0.1',
    author='Jannis Harder',
    author_email='jix@jixco.de',
    packages=find_packages(include='rattle.*'),
    extras_require={
        'dot': ['graphviz>=0.4']
    }
)
