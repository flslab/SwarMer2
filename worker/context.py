import random
import time
import numpy as np
from multiprocessing import shared_memory

import velocity
from config import Config
from utils import logger
from .metrics import MetricTypes


class WorkerContext:
    def __init__(self, count, fid, gtl, el, shm_name, metrics):
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
        self.shm_name = shm_name
        self.message_id = 0
        self.alpha = Config.DEAD_RECKONING_ANGLE / 180 * np.pi
        self.lease = dict()
        self.metrics = metrics
        self.set_swarm_id(self.fid)
        self.last_expanded = 0

    def set_swarm_id(self, swarm_id):
        # print(f"{self.fid}({self.swarm_id}) merged into {swarm_id}")
        self.swarm_id = swarm_id
        if self.shm_name:
            shared_mem = shared_memory.SharedMemory(name=self.shm_name)
            shared_array = np.ndarray((1,), dtype=np.float64, buffer=shared_mem.buf)
            shared_array[0] = self.swarm_id
            shared_mem.close()

        self.metrics.log_swarm_change(swarm_id)
        # self.history.log(MetricTypes.SWARM_ID, self.swarm_id)

    def set_el(self, el):
        self.el = el
        # if self.shm_name:
        #     shared_mem = shared_memory.SharedMemory(name=self.shm_name)
        #     shared_array = np.ndarray((5,), dtype=np.float64, buffer=shared_mem.buf)
        #     shared_array[:3] = self.el[:]
        #     shared_mem.close()

        self.metrics.log_coordinate_change(el)
        # self.history.log(MetricTypes.LOCATION, self.el)

    def set_query_id(self, query_id):
        self.query_id = query_id

    def set_challenge_id(self, challenge_id):
        self.challenge_id = challenge_id

    def set_anchor(self, anchor):
        self.anchor = anchor

    def set_radio_range(self, radio_range):
        self.radio_range = radio_range

    def deploy(self):
        self.metrics.log_illuminate(self.gtl)
        self.move(self.gtl - self.el)
        # if self.shm_name:
        #     shared_mem = shared_memory.SharedMemory(name=self.shm_name)
        #     shared_array = np.ndarray((1,), dtype=np.float64, buffer=shared_mem.buf)
        #     shared_array[4] = 0
        #     shared_mem.close()

    def fail(self):
        # if self.shm_name:
        #     shared_mem = shared_memory.SharedMemory(name=self.shm_name)
        #     shared_array = np.ndarray((5,), dtype=np.float64, buffer=shared_mem.buf)
        #     shared_array[4] = 2
        #     shared_mem.close()
        self.reset_swarm()
        self.set_el(np.array([.0, .0, .0]))
        self.radio_range = Config.INITIAL_RANGE
        self.anchor = None
        self.query_id = None
        self.challenge_id = None
        self.lease = dict()
        # self.history.log(MetricTypes.FAILURES, 1)
        self.metrics.log_sum("A5_num_failures", 1)
        self.metrics.log_failure()

    def move(self, vector):
        erred_v = self.add_dead_reckoning_error(vector)
        dest = self.el + erred_v
        # self.history.log(MetricTypes.LOCATION, self.el)
        self.metrics.log_sum("A0_total_distance", np.linalg.norm(vector))
        vm = velocity.VelocityModel(self.el, dest)
        vm.solve()
        dur = vm.total_time
        self.log_wait_time(dur)

        if Config.BUSY_WAITING:
            fin_time = time.time() + dur
            while True:
                if time.time() >= fin_time:
                    break
        else:
            time.sleep(dur)

        self.set_el(dest)

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
        if time.time() - self.last_expanded > 0.05:
            if self.radio_range < Config.MAX_RANGE:
                self.set_radio_range(self.radio_range + 5)

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
        meta = {"length": length}
        # self.history.log(MetricTypes.RECEIVED_MASSAGES, msg_type, meta)
        self.metrics.log_received_msg(msg_type, length)

    def log_dropped_messages(self):
        # self.history.log_sum(MetricTypes.DROPPED_MESSAGES)
        self.metrics.log_sum("A4_num_dropped_messages", 1)

    def log_sent_message(self, msg_type, length):
        meta = {"length": length}
        # self.history.log(MetricTypes.SENT_MESSAGES, msg_type, meta)
        self.metrics.log_sent_msg(msg_type, length)
        self.message_id += 1

    def log_expired_lease(self):
        # self.history.log_sum(MetricTypes.EXPIRED_LEASE)
        self.metrics.log_sum("A2_num_expired_leases", 1)
        self.metrics.log_lease_expiration()

    def log_canceled_lease(self):
        # self.history.log_sum(MetricTypes.CANCELED_LEASE)
        self.metrics.log_sum("A2_num_canceled_leases", 1)

    def log_released_lease(self):
        # self.history.log_sum(MetricTypes.RELEASED_LEASE)
        self.metrics.log_sum("A2_num_released_leases", 1)

    def log_granted_lease(self):
        # self.history.log_sum(MetricTypes.GRANTED_LEASE)
        self.metrics.log_sum("A2_num_granted_leases", 1)

    def log_wait_time(self, dur):
        # self.history.log(MetricTypes.WAITS, dur)
        self.metrics.log_sum("A1_num_moved", 1)
        self.metrics.log_sum("A1_total_wait(s)", dur)
        self.metrics.log_max("A1_max_wait(s)", dur)
        self.metrics.log_min("A1_min_wait(s)", dur)

    def log_localize(self):
        # self.history.log(MetricTypes.LOCALIZE, 1)
        self.metrics.log_sum("A3_num_localize", 1)

    def log_anchor(self):
        # self.history.log(MetricTypes.ANCHOR, 1)
        self.metrics.log_sum("A3_num_anchor", 1)

    def refresh_lease_table(self):
        expired_leases = []
        t = time.time()
        for fid, expiration_time in self.lease.items():
            if t > expiration_time:
                expired_leases.append(fid)

        for expired_lease in expired_leases:
            self.lease.pop(expired_lease)
            self.log_expired_lease()
            # print(f"anchor {self.fid} removed the lease for {expired_lease}")

    def grant_lease(self, fid):
        self.lease[fid] = time.time() + Config.CHALLENGE_LEASE_DURATION + 0.1
        self.log_granted_lease()

    def release_lease(self, fid):
        if fid in self.lease:
            self.lease.pop(fid)
            self.log_released_lease()

    def cancel_lease(self, fid):
        if fid in self.lease:
            self.lease.pop(fid)
            self.log_canceled_lease()

    def is_lease_empty(self):
        return len(self.lease) == 0

    def clear_lease_table(self):
        keys = list(self.lease.keys())
        for fid in keys:
            self.cancel_lease(fid)
