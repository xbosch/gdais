#!/bin/bash

GDAIS_PATH="/home/pau/feina/UPC/projecte/code/GDAIS/GDAIS-core"

# defaults
equipment="conf/equips/avio.json"
background=0

# read args
if [ $# -gt 2 ]; then
  echo "Too many arguments."
  exit 1
fi

if [ $# -eq 2 ]; then
  if [ "$1" != "-d" ]; then
    echo "Unknown option '$1'"
    exit 2
  fi
  background=1
  equipment="$2"
elif [ $# -eq 1 ]; then
  if [ "$1" == "-d" ]; then
    background=1
  else
    equipment="$1"
  fi
fi

# check no other GDAIS process is running
ps -eo cmd | grep main.py | grep python > /dev/null
if [ $? -eq 0 ]; then
  echo "GDAIS already running, only one instance can be started."
  exit 2
fi

# run GDAIS
if [ $background -eq 0 ]; then
  python "$GDAIS_PATH/main.py" $equipment
else
  # in background
  python "$GDAIS_PATH/main.py" -d $equipment &
fi
