#!/bin/bash
for i in {1..7..2}
do
   cp "./experiments/config$i.py" config.py
   sleep 1
   python server.py
done

for i in {2..8..2}
do
   cp "./experiments/config$i.py" config.py
   sleep 1
   python server.py
done