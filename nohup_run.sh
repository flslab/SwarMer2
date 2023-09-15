#!/bin/bash

nohup bash start_cluster.sh > my.log 2>&1 &
echo $! > save_pid.txt