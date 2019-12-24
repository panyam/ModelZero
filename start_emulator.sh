#!/bin/sh

numlines=`pyenv virtualenvs | grep "gcloudtools " | wc -l`

if [ "$numlines" = "0" ]; then
    pyenv virtualenv 2.7.16 gcloudtools
    pyenv shell 2.7.16
    pip install -r requirements.txt
    pip install -r dev_requirements.txt
    pip install --upgrade pip
fi

if [ "$1" = "reset" ]; then
    kill -9 `ps -ef | grep datastore-emulator | grep -v grep | sed -e "s/  */:/g" | cut -d ':' -f 2 `
    rm -Rf ./dsemu
fi

export DATASTORE_EMULATOR_HOST=localhost:8081
pyenv shell 2.7.16
gcloud beta emulators datastore start --data-dir=./dsemu --log-http
