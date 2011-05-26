#!/bin/bash
exec 3<> /dev/tcp/127.0.0.1/12345
echo -n "quit" 1>&3

