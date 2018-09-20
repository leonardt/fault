# Fault
[![Build Status](https://travis-ci.com/leonardt/fault.svg?branch=master)](https://travis-ci.com/leonardt/fault)
[![Coverage Status](https://coveralls.io/repos/github/leonardt/fault/badge.svg?branch=master)](https://coveralls.io/github/leonardt/fault?branch=master)

A Python package for testing hardware (part of the magma ecosystem).

## Developer Guide

### Branching and Release Model
Release follow [Semantic Versioning 2.0.0](https://semver.org/).

For those looking to contribute to fault, we are currently using a simpler
variant of the [git flow
model](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow).
This may change as the project grows (e.g. adopt a staging branch).  Currently,
there are two main branches that you should be aware of.  

1. *master* - This branch contains the release version of the code.
   Specifically, the latest commit on the *master* branches corresponds to the
   code that has been distributed to [PyPI](https://pypi.org/) via the
   [TravisCI](https://travis-ci.com/) script.

2. *dev* - The this branch is the *dev* branch.  This is where new features
   should be branched off of and pull requested into.  The
   [TravisCI](https://travis-ci.com/) script maintains an unversioned
   development release that is automatically built on successful *dev* builds
   (**TODO** Could be good to maintain some history of these builds, incase
   there are any regressions introduced that are not caught by the test suite).
   New features should be branched and merged into *dev* because releases are
   controlled by merges from *dev* into *master*.  This allows us to stage new
   features for release on the *dev* branch.  Users requiring new features that
   are only available on the *dev* branch should use the development release.
   Pull requests from *dev* into *master* should increase the second digit of
   the version numer in `setup.py`.

Branching and merging into *master* is acceptable for hotfix changes, for
example, fixing a bug in an existing feature. This model allows developers to
quickly address issues affecting user code, without having to wait for a new
release that may include new features.  Pull requests into master should
update the `setup.py` file with an increase in the third digit version number.

### Useful links
* [Deploying to PyPI via TravisCI](https://docs.travis-ci.com/user/deployment/pypi/)
