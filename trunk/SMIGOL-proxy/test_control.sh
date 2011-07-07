#!/bin/bash

TCP_PORT=20000

# start proxy process
echo "Starting proxy process..."
python smigol.py &

# wait for it to start
sleep 1

# try to connect
if ! exec 3<> /dev/tcp/localhost/$TCP_PORT; then
  echo "$(basename $0): unable to connect to localhost:$TCP_PORT"
  exit 1
fi

# wait for control connection established
sleep 1
echo "Ready!"
echo
echo "Now start GDAIS and then press enter to send start command"
read
echo "Sending 'start'..."
echo -n "s" 1>&3
echo
echo "Press enter to send quit command"
read
echo "Sending 'quit'..."
echo -n "q" 1>&3

exec 3<&-

exit 0

