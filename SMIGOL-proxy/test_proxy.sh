#!/bin/bash

if [ ! "$1" ]; then
  echo "usage: $(basename $0) [port]"
  exit 1
fi

port="$1"

# try to connect
if ! exec 3<> /dev/tcp/localhost/$port; then
  echo "$(basename $0): unable to connect to localhost:$port"
  exit 1
fi

while read 0<&3; do
  echo $REPLY >&2
  if [ "$REPLY" = "Finished!" ]; then 
    break
  fi
done

exec 3<&-

exit 0

