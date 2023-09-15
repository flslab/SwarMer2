class Config:
    GOSSIP_TIMEOUT = 5
    GOSSIP_SWARM_COUNT_THRESHOLD = 3
    THAW_SWARMS = False
    INITIAL_RANGE = 10
    MAX_RANGE = 200
    DROP_PROB_SENDER = 0
    DROP_PROB_RECEIVER = 0
    STATE_TIMEOUT = 0.4
    SIZE_QUERY_TIMEOUT = 10
    DEAD_RECKONING_ANGLE = 5
    CHALLENGE_PROB_DECAY = 5
    INITIAL_CHALLENGE_PROB = 1
    CHALLENGE_LEASE_DURATION = 0.2
    CHALLENGE_ACCEPT_DURATION = 0.01
    CHALLENGE_INIT_DURATION = 0
    FAILURE_TIMEOUT = 0
    FAILURE_PROB = 0
    NUMBER_ROUND = 5
    ACCELERATION = 6
    DECELERATION = 6
    MAX_SPEED = 6
    DISPLAY_CELL_SIZE = 0.05
    HD_TIMOUT = 5
    SIZE_QUERY_PARTICIPATION_PERCENT = 1
    DECENTRALIZED_SWARM_SIZE = False
    CENTRALIZED_SWARM_SIZE = False
    PROBABILISTIC_ROUND = False
    CENTRALIZED_ROUND = True
    BUSY_WAITING = False
    MIN_ADJUSTMENT = 0
    SAMPLE_SIZE = 0
    DURATION = 300
    SHAPE = 'chess'
    RESULTS_PATH = '/proj/nova-PG0/hamed/results/swarmer'
    MULTICAST = False
    THAW_MIN_NUM_SWARMS = 1
    THAW_PERCENTAGE_LARGEST_SWARM = 80
    THAW_INTERVAL = 1  # second
