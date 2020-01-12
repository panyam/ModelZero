#!/bin/sh

numlines=`pyenv virtualenvs | grep "gcloudtools " | wc -l`
if [ "$numlines" = "0" ]; then
    pyenv virtualenv 2.7.16 gcloudtools
    pyenv shell 2.7.16
    pip install -r requirements.txt
    pip install -r dev_requirements.txt
    pip install --upgrade pip
fi

PORT=8081

while getopts ":hrp:" opt; do
  case ${opt} in
    h ) # process option a
      echo "Usage:"
      echo "    $0 -h       Display this help message."
      echo "    $0 -r       Reset the datastore by removing all data."
      echo "    $0 -p       Port the emulator should be started on.  Default: 8081"
      exit 0
      ;;
    r)
        kill -9 `ps -ef | grep datastore-emulator | grep -v grep | sed -e "s/  */:/g" | cut -d ':' -f 2 `
        rm -Rf ./dsemu
      ;;
    p ) # process option t
      PORT=$OPTARG
      ;;
    \? )
      echo "Invalid Option: -$OPTARG" 1>&2
      exit 1
      ;;
  esac
done

shift $((OPTIND -1))

HOST_PORT="localhost:$PORT"
pyenv shell 2.7.16
gcloud beta emulators datastore start --data-dir=./dsemu --log-http --host-port=$HOST_PORT
