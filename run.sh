#!/bin/bash
python main.py 2>&1 | tee debug.log | cut -b -100
