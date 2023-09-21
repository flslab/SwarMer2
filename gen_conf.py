import itertools
import os

def_conf = {
    "GOSSIP_TIMEOUT": "5",
    "GOSSIP_SWARM_COUNT_THRESHOLD": "3",
    "THAW_SWARMS": "False",
    "INITIAL_RANGE": "10",
    "MAX_RANGE": "200",
    "DROP_PROB_SENDER": "0",
    "DROP_PROB_RECEIVER": "0",
    "STATE_TIMEOUT": "0.5",
    "SIZE_QUERY_TIMEOUT": "10",
    "DEAD_RECKONING_ANGLE": "5",
    "CHALLENGE_PROB_DECAY": "1.25",
    "INITIAL_CHALLENGE_PROB": "1",
    "CHALLENGE_LEASE_DURATION": "0.25",
    "CHALLENGE_ACCEPT_DURATION": "0.02",
    "CHALLENGE_INIT_DURATION": "0",
    "FAILURE_TIMEOUT": "0",
    "FAILURE_PROB": "0",
    "NUMBER_ROUND": "5",
    "ACCELERATION": "10",
    "DECELERATION": "10",
    "MAX_SPEED": "10",
    "DISPLAY_CELL_SIZE": "0.05",
    "HD_TIMOUT": "5",
    "SIZE_QUERY_PARTICIPATION_PERCENT": "1",
    "DECENTRALIZED_SWARM_SIZE": "False",
    "CENTRALIZED_SWARM_SIZE": "False",
    "PROBABILISTIC_ROUND": "False",
    "CENTRALIZED_ROUND": "True",
    "BUSY_WAITING": "False",
    "MIN_ADJUSTMENT": "0",
    "SAMPLE_SIZE": "0",
    "DURATION": "120",
    "SHAPE": "'chess'",
    "RESULTS_PATH": "'/proj/nova-PG0/hamed/results/swarmer'",
    "MULTICAST": "False",
    "THAW_MIN_NUM_SWARMS": "1",
    "THAW_PERCENTAGE_LARGEST_SWARM": "80",
    "THAW_INTERVAL": "1  # second",
}

props = [
    {
        "keys": ["STATE_TIMEOUT"],
        "values": ["0.05", "0.1", "0.15", "0.20", "0.25", "0.3", "0.35", "0.4", "0.45", "0.5", "0.55",
                   "0.6", "0.65", "0.7", "0.75", "0.8", "0.85", "0.9", "0.95", "1", "1.05",
                   "1.1", "1.15", "1.2", "1.25", "1.3", "1.35", "1.4", "1.45", "1.5"]
    },
    # {
    #     "keys": ["ACCELERATION", "DECELERATION", "MAX_SPEED"],
    #     "values": ["1.5", "6"]
    # },
    {
        "keys": ["SHAPE"],
        "values": ["'chess'"]
    },
]


if __name__ == '__main__':
    props_values = [p["values"] for p in props]
    print(props_values)
    combinations = list(itertools.product(*props_values))
    print(len(combinations))

    if not os.path.exists('experiments'):
        os.makedirs('experiments', exist_ok=True)

    for j in range(len(combinations)):
        c = combinations[j]
        conf = def_conf.copy()
        for i in range(len(c)):
            for k in props[i]["keys"]:
                conf[k] = c[i]
        with open(f'experiments/config{j}.py', 'w') as f:
            f.write('class Config:\n')
            for key, val in conf.items():
                f.write(f'    {key} = {val}\n')

