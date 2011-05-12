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

# run GDAIS
python main.py $equipment 2>&1 | tee debug.log | cut -b -100
