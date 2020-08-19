"""
Setup file for fault
"""

from setuptools import setup

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

DESCRIPTION = """\
A Python package for testing hardware (part of the magma ecosystem)\
"""

setup(
    name='fault',
    version='3.0.30',
    description=DESCRIPTION,
    scripts=[],
    packages=[
        "fault",
        "fault.tester",
    ],
    install_requires=[
        "astor",
        "coreir",
        "cosa",
        "z3-solver",
        "hwtypes",
        "magma-lang>=2.0.73",
        "pyyaml",
        "scipy",
        "numpy",
        "DeCiDa"
    ],
    license='BSD License',
    url='https://github.com/leonardt/fault',
    author='Leonard Truong',
    author_email='lenny@cs.stanford.edu',
    python_requires='>=3.6',
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown"
)
