#!/bin/bash
for i in {0..5}
do
   cp "./experiments/config$i.py" config.py
   sleep 20
   /Users/hamed/Documents/Holodeck/SwarMerPy/venv/bin/python /Users/hamed/Documents/Holodeck/SwarMer2/server.py
done
