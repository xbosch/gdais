#!/bin/bash

PROXY_PORT=20000

GDAIS_PATH="/home/pau/feina/UPC/projecte/code/GDAIS/GDAIS-core"
GDAIS_PORT=12345

# start proxy process
echo "Starting proxy process..."
python smigol.py &

# wait for it to start
sleep 1

# try to connect to the proxy
if ! exec 3<> /dev/tcp/localhost/$PROXY_PORT; then
  echo "$(basename $0): unable to connect to proxy localhost:$PROXY_PORT"
  exit 1
fi

# wait for control connection established
sleep 1
echo "proxy started!"
echo

echo "Now starting GDAIS..."
$GDAIS_PATH/run.sh -d $GDAIS_PATH/conf/equips/smigol.json

# wait for it to start
sleep 2

# try to connect to GDAIS
if ! exec 4<> /dev/tcp/localhost/$GDAIS_PORT; then
  echo "$(basename $0): unable to connect to GDAIS localhost:$GDAIS_PORT"
  # stop proxy and clear connection
  echo -n "s" 1>&3
  echo -n "q" 1>&3
  exec 3<&-
  exit 2
fi

echo "Set GDAIS log level to WARNING"
echo -n "set_log_level 30" 1>&4

echo "GDAIS started!"
echo 

# wait more
sleep 1

echo "Sending 'start' to proxy..."
echo -n "s" 1>&3
echo

echo "Waiting for proxy to finish..."
wait
echo "Proxy process exited"
echo

echo "Sending 'quit' to GDAIS..."
echo -n "quit" 1>&4
exec 4<&-

echo "Finished!"
exit 0

