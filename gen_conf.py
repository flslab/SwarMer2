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
    "SAMPLE_SIZE": "100",
    "DURATION": "120",
    "SHAPE": "'chess'",
    "RESULTS_PATH": "'/proj/nova-PG0/hamed/results/swarmer'",
    "MULTICAST": "False",
    "THAW_MIN_NUM_SWARMS": "1",
    "THAW_PERCENTAGE_LARGEST_SWARM": "80",
    "THAW_INTERVAL": "1  # second",
    "SS_ERROR_MODEL": "0",
    "SS_ERROR_PERCENTAGE": "0.1",
    "SS_ACCURACY_PROBABILITY": "0.9",
    "FILE_NAME_KEYS": "[]",
    "SS_NUM_SAMPLES": "10",
    "SS_SAMPLE_DELAY": "0",
    "DIR_KEYS": "[('SS_ERROR_MODEL', 'EM'), ('SS_NUM_SAMPLES', 'NS')]",
}

props = [
    {
        "keys": ["SS_NUM_SAMPLES"],
        "values": ["10", "20", "100", "1000"]
    },
    {
        "keys": ["SS_ERROR_MODEL", "SS_ERROR_PERCENTAGE", "SS_ACCURACY_PROBABILITY", "FILE_NAME_KEYS"],
        "values": [
            # {"SS_ERROR_MODEL": "0", "SS_ERROR_PERCENTAGE": "0.1", "SS_ACCURACY_PROBABILITY": "0.9", "FILE_NAME_KEYS": "[]"},
            {"SS_ERROR_MODEL": "1", "SS_ERROR_PERCENTAGE": "0.01", "SS_ACCURACY_PROBABILITY": "0.99", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.01", "SS_ACCURACY_PROBABILITY": "0.99", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "3", "SS_ERROR_PERCENTAGE": "0.01", "SS_ACCURACY_PROBABILITY": "0.99", "FILE_NAME_KEYS": "[('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "1", "SS_ERROR_PERCENTAGE": "0.1", "SS_ACCURACY_PROBABILITY": "0.9", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X')]"},
            # {"SS_ERROR_MODEL": "1", "SS_ERROR_PERCENTAGE": "0.5", "SS_ACCURACY_PROBABILITY": "0.9", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X')]"},
            # {"SS_ERROR_MODEL": "1", "SS_ERROR_PERCENTAGE": "0.9", "SS_ACCURACY_PROBABILITY": "0.9", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.1", "SS_ACCURACY_PROBABILITY": "0.9", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.1", "SS_ACCURACY_PROBABILITY": "0.5", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.1", "SS_ACCURACY_PROBABILITY": "0.1", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.5", "SS_ACCURACY_PROBABILITY": "0.9", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.5", "SS_ACCURACY_PROBABILITY": "0.5", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.5", "SS_ACCURACY_PROBABILITY": "0.1", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.9", "SS_ACCURACY_PROBABILITY": "0.9", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.9", "SS_ACCURACY_PROBABILITY": "0.5", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "2", "SS_ERROR_PERCENTAGE": "0.9", "SS_ACCURACY_PROBABILITY": "0.1", "FILE_NAME_KEYS": "[('SS_ERROR_PERCENTAGE', 'X'), ('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "3", "SS_ERROR_PERCENTAGE": "0.1", "SS_ACCURACY_PROBABILITY": "0.9", "FILE_NAME_KEYS": "[('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "3", "SS_ERROR_PERCENTAGE": "0.1", "SS_ACCURACY_PROBABILITY": "0.5", "FILE_NAME_KEYS": "[('SS_ACCURACY_PROBABILITY', 'P')]"},
            # {"SS_ERROR_MODEL": "3", "SS_ERROR_PERCENTAGE": "0.1", "SS_ACCURACY_PROBABILITY": "0.1", "FILE_NAME_KEYS": "[('SS_ACCURACY_PROBABILITY', 'P')]"},
        ]
    },
]

if __name__ == '__main__':
    file_name = "config"
    class_name = "Config"

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
                if isinstance(c[i], dict):
                    conf[k] = c[i][k]
                else:
                    conf[k] = c[i]
        with open(f'experiments/{file_name}{j}.py', 'w') as f:
            f.write(f'class {class_name}:\n')
            for key, val in conf.items():
                f.write(f'    {key} = {val}\n')
