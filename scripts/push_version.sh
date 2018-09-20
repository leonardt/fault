#!/bin/sh

# From https://gist.github.com/willprice/e07efd73fb7f13f917ea#file-push-sh

git config --global user.email "travis@travis-ci.org"
git config --global user.name "Travis CI"

git add VERSION
git add PYVERSION
git commit --message "Travis build: $TRAVIS_BUILD_NUMBER"

git push --quiet 
