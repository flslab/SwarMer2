#!/bin/bash
for i in {1..8}
do
   cp "./experiments/config$i.py" config.py
   python server.py
done