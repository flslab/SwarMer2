import time
from config import Config
from utils import logger


class WorkerContext:
    def __init__(self, count, fid, gtl, el):
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
        self.history_el = {time.time(): self.el}
        self.history_swarm_id = {time.time(): self.swarm_id}

    def set_swarm_id(self, swarm_id):
        self.swarm_id = swarm_id
        self.history_swarm_id[time.time()] = self.swarm_id

    def set_el(self, el):
        self.el = el
        self.history_el[time.time()] = self.el

    def set_query_id(self, query_id):
        self.query_id = query_id

    def set_challenge_id(self, challenge_id):
        self.challenge_id = challenge_id

    def set_anchor(self, anchor):
        self.anchor = anchor

    def move(self, vector):
        self.set_el(self.el + vector)

    def update_neighbor(self, ctx):
        self.neighbors[ctx.fid] = ctx.swarm_id

    def increment_range(self):
        if self.radio_range < Config.MAX_RANGE:
            self.radio_range += 1
            logger.critical(f"{self.fid} range incremented to {self.radio_range}")

    def reset_range(self):
        self.radio_range = Config.INITIAL_RANGE

    def reset_swarm(self):
        self.swarm_id = self.fid

    def thaw_swarm(self):
        self.reset_swarm()
        self.reset_range()
        self.size = 1
        self.anchor = None
        self.query_id = None
        self.challenge_id = None
