import itertools
import os

def_conf = {
    "THAW_SWARMS": "False",
    "INITIAL_RANGE": "5",
    "MAX_RANGE": "200",
    "DROP_PROB_SENDER": "0",
    "DROP_PROB_RECEIVER": "0",
    "STATE_TIMEOUT": "0.4",
    "SIZE_QUERY_TIMEOUT": "10",
    "DEAD_RECKONING_ANGLE": "5",
    "CHALLENGE_PROB_DECAY": "5",
    "INITIAL_CHALLENGE_PROB": "1",
    "CHALLENGE_LEASE_DURATION": "3600",
    "FAILURE_TIMEOUT": "0",
    "FAILURE_PROB": "0",
    "NUMBER_ROUND": "5",
    "ACCELERATION": "6",
    "DECELERATION": "6",
    "MAX_SPEED": "6",
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
    "DURATION": "600",
    "SHAPE": "'chess'",
    "RESULTS_PATH": "'results'",
    "MULTICAST": "True",
}

props = [
    # {
    #     "keys": ["DROP_PROB_RECEIVER"],
    #     "values": ["0", "0.1", "0.01", "0.001"]
    # },
    # {
    #     "keys": ["ACCELERATION", "DECELERATION", "MAX_SPEED"],
    #     "values": ["1.5", "6"]
    # },
    {
        "keys": ["SHAPE"],
        "values": ["'dragon'"]
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

