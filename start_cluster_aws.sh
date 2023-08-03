#!/bin/bash

source aws_vars.sh

now=$(date +%d_%b_%H_%M_%S)
port="6000"
for (( i=1; i<N; i++ )); do
    server_addr=${USERNAME}@${HOSTNAMES[$i]}
    ssh -o ConnectionAttempts=60 -oStrictHostKeyChecking=no -i ${LOCAL_KEY_PATH} "${server_addr}" "ulimit -n 9999 && cd SwarMer && cp experiments/test_config$1.py test_config.py && sleep 10 && nohup python3 server.py ${N} ${i} ${now} ${port} > my.log 2>&1 &" &
done

ulimit -n 9999 && cp "experiments/test_config$1.py" test_config.py && sleep 1 && python3 server.py "${N}" 0 "${now}" "${port}"
