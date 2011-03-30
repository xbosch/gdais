#!/bin/bash
python main.py | tee debug.log | cut -b -100
