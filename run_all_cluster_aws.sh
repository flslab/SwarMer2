#!/bin/bash

bash gen_conf_cluster_aws.sh
sleep 10

directory="experiments"

# Number of configuration files (experiments)
count=$(find "$directory" -type f -name "*.py" | wc -l)

repetitions=1

for ((i = 0; i < count; i++)); do
  for ((j = 1; j <= repetitions; j++)); do
     echo ""
     echo "config: $i," "repetition: $j"
     bash start_cluster_aws.sh "$i"
     sleep 10
     pkill python3.9
  done
done
