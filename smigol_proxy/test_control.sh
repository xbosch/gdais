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

echo "Press enter to send start command"
read
echo "Sending 'start'..."
echo -n "s" 1>&3

echo "Press enter to send quit command"
read
echo "Sending 'quit'..."
echo -n "q" 1>&3

exec 3<&-

exit 0

