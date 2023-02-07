from enum import Enum


class MessageTypes(Enum):
    STOP = 0
    DUMMY = 99
    CHALLENGE = 1
    ACCEPT_CHALLENGE = 2
    ACK_CHALLENGE = 3
    FIN_CHALLENGE = 4
    QUERY_SIZE = 5
    SIZE_REPLY = 6
    FOLLOW_MERGE = 7
    SET_BUSY = 8
    SET_AVAILABLE = 9
