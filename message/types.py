from enum import Enum


class MessageTypes(Enum):
    STOP = 0
    DUMMY = 99
    CHALLENGE_INIT = 1
    CHALLENGE_ACCEPT = 2
    CHALLENGE_ACK = 3
    CHALLENGE_FIN = 4
    FOLLOW = 5
    MERGE = 6
    FOLLOW_MERGE = 7
    SET_AVAILABLE = 8
    SET_WAITING = 9
    LEASE_GRANT = 10
    LEASE_RENEW = 11
    SIZE_QUERY = 12
    SIZE_REPLY = 13
    THAW_SWARM = 14
    FIN = 15

