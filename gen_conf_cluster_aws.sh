#!/bin/bash

source aws_vars.sh

python3 gen_conf.py -t

for (( i=1; i<N; i++ )); do
    server_addr=${USERNAME}@${HOSTNAMES[$i]}
    ssh -oStrictHostKeyChecking=no -i ${LOCAL_KEY_PATH} "${server_addr}" "cd SwarMer && python3 gen_conf.py -t" &
done
