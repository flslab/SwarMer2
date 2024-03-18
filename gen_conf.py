import itertools
import os

def_conf = {
    "GOSSIP_TIMEOUT": "5",
    "GOSSIP_SWARM_COUNT_THRESHOLD": "3",
    "THAW_SWARMS": "False",
    "INITIAL_RANGE": "200",
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
    "DURATION": "60",
    "SHAPE": "'outring'",
    "RESULTS_PATH": "'/proj/nova-PG0/hamed/results/swarmer'",
    "MULTICAST": "False",
    "THAW_MIN_NUM_SWARMS": "1",
    "THAW_PERCENTAGE_LARGEST_SWARM": "80",
    "THAW_INTERVAL": "1",
    "SS_ERROR_MODEL": "1",
    "SS_ERROR_PERCENTAGE": "0.1",
    "SS_ACCURACY_PROBABILITY": "0.9",
    "SS_NUM_SAMPLES": "1",
    "SS_SAMPLE_DELAY": "0",
    "STANDBY": "False",
    "GROUP": "False",
    "GROUP_TYPE": "'sequential'",
    "FILE_NAME_KEYS": "[('DEAD_RECKONING_ANGLE', 'D'), ('SS_ERROR_PERCENTAGE', 'X'), ('SHAPE', 'S')]",
    "DIR_KEYS": "[('SHAPE', 'S')]",
}

props = [
    {
        "keys": ["SHAPE"],
        "values": ["'grid_25_hierarchical'", "'grid_400_hierarchical'", "'chess_hierarchical'"]
    },
    {
        "keys": ["DEAD_RECKONING_ANGLE", "SS_ERROR_PERCENTAGE"],
        "values": [
            {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0.0"},
            {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0.01"},
            {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0.1"},

            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'10'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'50'"},
            #
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.01", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.05", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.1", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.01", "SHAPE": "'50'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.05", "SHAPE": "'50'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.1", "SHAPE": "'50'"},
            #
            # {"DEAD_RECKONING_ANGLE": "1", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "3", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "1", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'50'"},
            # {"DEAD_RECKONING_ANGLE": "3", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'50'"},
            # {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'50'"},
            #
            # {"DEAD_RECKONING_ANGLE": "1", "SS_ERROR_PERCENTAGE": "0.01", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "3", "SS_ERROR_PERCENTAGE": "0.05", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0.1", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "1", "SS_ERROR_PERCENTAGE": "0.01", "SHAPE": "'50'"},
            # {"DEAD_RECKONING_ANGLE": "3", "SS_ERROR_PERCENTAGE": "0.05", "SHAPE": "'50'"},
            # {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0.1", "SHAPE": "'50'"},
            #
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.01", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.01", "SHAPE": "'10'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.01", "SHAPE": "'50'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.1", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.1", "SHAPE": "'10'"},
            # {"DEAD_RECKONING_ANGLE": "0", "SS_ERROR_PERCENTAGE": "0.1", "SHAPE": "'50'"},
            #
            # {"DEAD_RECKONING_ANGLE": "1", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "1", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'10'"},
            # {"DEAD_RECKONING_ANGLE": "1", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'50'"},
            # {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'2'"},
            # {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'10'"},
            # {"DEAD_RECKONING_ANGLE": "5", "SS_ERROR_PERCENTAGE": "0", "SHAPE": "'50'"},
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
