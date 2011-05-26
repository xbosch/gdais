#!/bin/bash

# defaults
equipment="conf/equips/avio.json"

# read args
if [ $# -gt 1 ]; then
  echo "Too many arguments."
  exit 1
fi

if [ $# -eq 1 ]; then
  equipment="$1"
fi

# check no other GDAIS process is running
ps -eo cmd | grep main.py | grep python > /dev/null
if [ $? -eq 0 ]; then
  echo "GDAIS already running, only one instance can be started."
  exit 2
fi

# run GDAIS
python main.py $equipment 2>&1 | tee debug.log | cut -b -100
