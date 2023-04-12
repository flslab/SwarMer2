import time
import numpy as np
from multiprocessing import shared_memory
from config import Config
from utils import logger
from .history import History


class WorkerContext:
    RECEIVED_MASSAGES = 0
    SENT_MESSAGES = 1
    LOCATION = 2
    SWARM_ID = 3

    def __init__(self, count, fid, gtl, el, shm_name):
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
        self.shm_name = shm_name
        self.message_id = 0
        self.speed = Config.FLS_SPEED
        self.alpha = Config.DEAD_RECKONING_ANGLE / 180 * np.pi
        self.lease = dict()

    def set_swarm_id(self, swarm_id):
        print(f"{self.fid}({self.swarm_id}) merged into {swarm_id}")
        self.swarm_id = swarm_id
        self.history.log(WorkerContext.SWARM_ID, self.swarm_id)

    def set_el(self, el):
        self.el = el
        if self.shm_name:
            shared_mem = shared_memory.SharedMemory(name=self.shm_name)
            shared_array = np.ndarray((3,), dtype=np.float64, buffer=shared_mem.buf)
            shared_array[:] = self.el[:]
            shared_mem.close()
        # print(self.shared_array)
        # if self.shared_array:
        #     self.shared_array[:] = self.el[:]
        #     print(self.shared_array)
            # np.put(self.shared_array, [0, 1, 2], self.el)
        self.history.log(WorkerContext.LOCATION, self.el)

    def set_query_id(self, query_id):
        self.query_id = query_id

    def set_challenge_id(self, challenge_id):
        self.challenge_id = challenge_id

    def set_anchor(self, anchor):
        self.anchor = anchor

    def set_radio_range(self, radio_range):
        self.radio_range = radio_range

    def deploy(self):
        self.move(self.gtl - self.el)

    def fail(self):
        self.set_el(np.array([.0, .0, .0]))

    def move(self, vector):
        erred_v = self.add_dead_reckoning_error(vector)
        self.history.log(WorkerContext.LOCATION, self.el)
        time.sleep(np.linalg.norm(erred_v) / self.speed)
        self.set_el(self.el + erred_v)

    def add_dead_reckoning_error(self, vector):
        if vector[0] or vector[1]:
            i = np.array([vector[1], -vector[0], 0])
        elif vector[2]:
            i = np.array([vector[2], 0, -vector[0]])
        else:
            return vector

        if self.alpha == 0:
            return vector

        j = np.cross(vector, i)
        norm_i = np.linalg.norm(i)
        norm_j = np.linalg.norm(j)
        norm_v = np.linalg.norm(vector)
        i = i / norm_i
        j = j / norm_j
        phi = np.random.uniform(0, 2 * np.pi)
        error = np.sin(phi) * i + np.cos(phi) * j
        r = np.linalg.norm(vector) * np.tan(self.alpha)

        erred_v = vector + np.random.uniform(0, r) * error
        return norm_v * erred_v / np.linalg.norm(erred_v)

    def update_neighbor(self, ctx):
        self.neighbors[ctx.fid] = ctx.swarm_id

    def increment_range(self):
        if self.radio_range < Config.MAX_RANGE:
            self.set_radio_range(self.radio_range + 1)
            logger.critical(f"{self.fid} range incremented to {self.radio_range}")
            return True
        else:
            return False

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

    def log_received_message(self, msg_type, length):
        # self.shared_mem["received_bytes"][self.fid - 1] = length
        meta = {"length": length}
        self.history.log(WorkerContext.RECEIVED_MASSAGES, msg_type, meta)

    def log_sent_message(self, msg_type, length):
        # self.shared_mem["sent_bytes"][self.fid - 1] = length
        meta = {"length": length}
        self.history.log(WorkerContext.SENT_MESSAGES, msg_type, meta)
        self.message_id += 1

    def get_location_history(self):
        return self.history[WorkerContext.LOCATION]

    def get_received_messages(self):
        return self.history[WorkerContext.RECEIVED_MASSAGES]

    def get_sent_messages(self):
        return self.history[WorkerContext.SENT_MESSAGES]

    def refresh_lease_table(self):
        expired_leases = []
        for fid, expiration_time in self.lease.items():
            if time.time() > expiration_time:
                expired_leases.append(fid)

        for expired_lease in expired_leases:
            self.lease.pop(expired_lease)
            # print(f"anchor {self.fid} removed the lease for {expired_lease}")

    def grant_lease(self, fid):
        self.lease[fid] = time.time() + Config.CHALLENGE_LEASE_DURATION
        # print(f"anchor {self.fid} granted lease for {fid}")

    def is_lease_empty(self):
        # print(f"len lease for {self.fid} is {len(self.lease)}")
        return len(self.lease) == 0

    def clear_lease_table(self):
        self.lease.clear()
