import time
import numpy as np
from config import Config
from utils import logger
from .history import History


class WorkerContext:
    RECEIVED_MASSAGES = 0
    SENT_MESSAGES = 1
    LOCATION = 2
    SWARM_ID = 3

    def __init__(self, count, fid, gtl, el, shared_el):
        self.count = count
        self.fid = fid
        self.gtl = gtl
        self.el = el
        self.swarm_id = self.fid
        self.neighbors = dict()
        self.radio_range = Config.INITIAL_RANGE
        self.size = 1
        self.anchor = None
        self.query_id = None
        self.challenge_id = None
        self.history = History(4)
        self.history.log(WorkerContext.LOCATION, self.el)
        self.history.log(WorkerContext.SWARM_ID, self.swarm_id)
        self.shared_el = shared_el
        self.message_id = 0
        self.speed = 1

    def set_swarm_id(self, swarm_id):
        self.swarm_id = swarm_id
        self.history.log(WorkerContext.SWARM_ID, self.swarm_id)

    def set_el(self, el):
        self.el = el
        self.shared_el[self.fid - 1] = el
        self.history.log(WorkerContext.LOCATION, self.el)

    def set_query_id(self, query_id):
        self.query_id = query_id

    def set_challenge_id(self, challenge_id):
        self.challenge_id = challenge_id

    def set_anchor(self, anchor):
        self.anchor = anchor

    def set_radio_range(self, radio_range):
        self.radio_range = radio_range

    def move(self, vector):
        time.sleep(np.linalg.norm(vector) / self.speed)
        self.set_el(self.el + vector)

    def update_neighbor(self, ctx):
        self.neighbors[ctx.fid] = ctx.swarm_id

    def increment_range(self):
        if self.radio_range < Config.MAX_RANGE:
            self.set_radio_range(self.radio_range + 1)
            logger.critical(f"{self.fid} range incremented to {self.radio_range}")

    def reset_range(self):
        self.set_radio_range(Config.INITIAL_RANGE)

    def reset_swarm(self):
        self.set_swarm_id(self.fid)

    def thaw_swarm(self):
        self.reset_swarm()
        self.reset_range()
        self.size = 1
        self.anchor = None
        self.query_id = None
        self.challenge_id = None

    def log_received_message(self, msg):
        self.history.log(WorkerContext.RECEIVED_MASSAGES, msg)

    def log_sent_message(self, msg):
        self.history.log(WorkerContext.SENT_MESSAGES, msg)
        self.message_id += 1
