#!/usr/bin/env bash

echo [distutils]                                  > ~/.pypirc
echo index-servers =                             >> ~/.pypirc
echo "  pypi"                                    >> ~/.pypirc
echo                                             >> ~/.pypirc
echo [pypi]                                      >> ~/.pypirc
echo repository=https://upload.pypi.org/legacy/  >> ~/.pypirc
echo username=__token__                          >> ~/.pypirc
echo password=$PYPI_TOKEN                        >> ~/.pypirc

python setup.py sdist build

twine upload dist/*
