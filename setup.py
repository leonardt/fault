from setuptools import setup
import sys

setup(
    name='fault',
    version='0.41',
    description='A Python package for testing hardware (part of the magma ecosystem)',
    scripts=[],
    packages=[
        "fault",
    ],
    install_requires=[
        "astor"
    ],
    license='BSD License',
    url='https://github.com/leonardt/fault',
    author='Leonard Truong',
    author_email='lenny@cs.stanford.edu',
    python_requires='>=3.6'
)
