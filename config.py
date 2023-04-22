class Config:
    THAW_SWARMS = False
    INITIAL_RANGE = 5
    MAX_RANGE = 200
    DROP_PROB_SENDER = 0
    DROP_PROB_RECEIVER = 0.01
    STATE_TIMEOUT = 1
    SIZE_QUERY_TIMEOUT = 10
    DEAD_RECKONING_ANGLE = 5
    CHALLENGE_PROB_DECAY = 5
    INITIAL_CHALLENGE_PROB = 1
    CHALLENGE_LEASE_DURATION = 0.5
    FAILURE_TIMEOUT = 3 * 24 * 3600
    NUMBER_ROUND = 5
    ACCELERATION = 3
    DECELERATION = 3
    MAX_SPEED = 3
    DISPLAY_CELL_SIZE = 0.05
    HD_TIMOUT = 5
    SIZE_QUERY_PARTICIPATION_PERCENT = 1
    DECENTRALIZED_SWARM_SIZE = False
    CENTRALIZED_SWARM_SIZE = True
    SAMPLE_SIZE = 0
    SHAPE = 'dragon'
    RESULTS_PATH = 'results'
