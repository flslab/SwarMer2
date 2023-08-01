#!/bin/bash
for i in {0..2}
do
   cp "./experiments/config$i.py" config.py
   sleep 1
   python3 server.py
done
