from setuptools import setup
import sys

with open("README.md", "r") as fh:
    long_description = fh.read()

description = """\
A Python package for testing hardware (part of the magma ecosystem)\
"""

setup(
    name='fault',
    version='2.0.7',
    description=description,
    scripts=[],
    packages=[
        "fault",
    ],
    install_requires=[
        "astor",
        "coreir",
        "cosa",
        "z3-solver",
        "hwtypes==1.0.*",
        "magma-lang"
    ],
    license='BSD License',
    url='https://github.com/leonardt/fault',
    author='Leonard Truong',
    author_email='lenny@cs.stanford.edu',
    python_requires='>=3.6',
    long_description=long_description,
    long_description_content_type="text/markdown"
)
