#!/bin/sh

export DATASTORE_EMULATOR_HOST=localhost:8081
kill -9 `ps -ef | grep datastore-emulator | grep -v grep | sed -e "s/  */:/g" | cut -d ':' -f 2 `
rm -Rf ../dsemu
gcloud beta emulators datastore start --data-dir=../dsemu &

echo "Running tests with mem store"
export FLASK_DATA_STORE=mem
pytest -s

echo "Running tests with cloud store"
export FLASK_DATA_STORE=gae
pytest -s

