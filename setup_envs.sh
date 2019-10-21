#!/bin/sh

pyenv virtualenv 2.7.16 gcloudtools
pyenv shell 2.7.16
pip install -r requirements.txt
pip install -r dev_requirements.txt
pip install --upgrade pip

pyenv virtualenv 3.7.0 modelzero
pyenv shell 3.7.0
pip install -r requirements.txt
pip install -r dev_requirements.txt
pyenv activate gcloudtools
pip install --upgrade pip
