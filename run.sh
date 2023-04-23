#!/bin/bash
for i in {1..6}
do
   cp "./experiments/config$i.py" config.py
   sleep 1
   python server.py
done
