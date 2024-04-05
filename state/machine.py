import json
import os
import random
import time
from enum import Enum

import numpy as np
import threading
import uuid


from message import Message, MessageTypes
from config import Config
from utils import logger
from worker.network import PrioritizedItem
from .types import StateTypes
from scipy.spatial.transform import Rotation


def add_ss_error_1(v, d, x=Config.SS_ERROR_PERCENTAGE):
    if d < 1e-9:
        return v, d
    new_d = d + x * d * (random.random())
    return v / d * new_d, new_d


def add_ss_error_1_1(v, d, x=Config.SS_ERROR_PERCENTAGE):
    if d < 1e-9:
        return v, d
    new_d = d + x * d * (random.random() * 2 - 1)
    return v / d * new_d, new_d


def add_ss_error_2(v, d):
    p = Config.SS_ACCURACY_PROBABILITY  # probability of being accurate
    if random.random() <= p:
        return v, d
    else:
        return add_ss_error_1(v, d)


def add_ss_error_3(v, d):
    p = Config.SS_ACCURACY_PROBABILITY  # probability of being accurate
    if random.random() <= p:
        return v, d
    else:
        return add_ss_error_1(v, d, x=random.random() * 2)


def sample_distance(_v, _d):
    vs = []
    ds = []

    for i in range(Config.SS_NUM_SAMPLES):
        if Config.SS_ERROR_MODEL == 1:
            v, d = add_ss_error_1(_v, _d)
        elif Config.SS_ERROR_MODEL == 2:
            v, d = add_ss_error_2(_v, _d)
        elif Config.SS_ERROR_MODEL == 3:
            v, d = add_ss_error_3(_v, _d)
        else:
            v, d = _v, _d

        vs.append(v)
        ds.append(d)

    if Config.SS_SAMPLE_DELAY:
        time.sleep(Config.SS_SAMPLE_DELAY * Config.SS_NUM_SAMPLES)

    # median
    # median_d = np.median(ds)
    # return _v * median_d / _d, median_d

    # average
    avg_d = np.average(ds)
    return _v * avg_d / _d, avg_d


class Mode (Enum):
    WITHIN_GROUP = 1
    INTER_GROUP = 2
    ANCHOR = 3


class StateMachine:
    def __init__(self, context, sock, metrics, event_queue):
        self.last_challenge_init = 0
        self.last_challenge_accept = 0
        self.state = StateTypes.DEPLOYING
        self.context = context
        self.metrics = metrics
        self.sock = sock
        self.should_fail = False
        self.event_queue = event_queue
        self.start_time = 0
        self.waiting_mode = False
        self.num_localizations = 0
        self.notified = False
        self.working_mode = Mode.WITHIN_GROUP

    def start(self):
        if Config.GROUP_TYPE == 'mst':
            self.localize = self.localize_mst
        elif Config.GROUP_TYPE == 'universal':
            self.localize = self.localize_universal
        elif Config.GROUP_TYPE == 'spanning_2' or Config.GROUP_TYPE == 'spanning_3':
            self.localize = self.localize_spanning_2
        elif Config.GROUP_TYPE == 'spanning_2_v2':
            self.localize = self.localize_spanning_2_variant_2
        elif Config.GROUP_TYPE == 'spanning_2_v3':
            self.localize = self.localize_spanning_2_variant_3
        elif Config.GROUP_TYPE == 'overlapping' or Config.GROUP_TYPE == 'bin_overlapping':
            self.localize = self.localize_overlapping
        elif Config.GROUP_TYPE == 'spanning':
            self.localize = self.localize_spanning
        elif Config.GROUP_TYPE == 'hierarchical':
            self.localize = self.localize_hierarchical
        else:
            self.localize = self.localize_sequential_hierarchical
        self.context.deploy()
        self.start_time = time.time()
        self.enter(StateTypes.AVAILABLE)

    def handle_follow(self, msg):
        self.context.move(msg.args[0])
        # if Config.GROUP_TYPE == 'sequential':
        #     self.context.go_to_next_hierarchy()
        self.context.neighbors = {}
        # if Config.GROUP_TYPE == 'mst':
        #     for fid in self.context.anchor_for:
        #         self.broadcast(Message(MessageTypes.FOLLOW, args=(msg.args[0],)).to_fls_id(fid, '*'))
        if msg.args[1]:
            self.waiting_mode = False

            for fid, gid in self.context.localizer:
                if gid is None:
                    self.broadcast(Message(MessageTypes.NOTIFY).to_fls_id(fid, "*"))
                # print(f"{self.context.fid} notified {fid}")

        # print(f"({msg.fid}) -> {self.context.fid} followed")

    def handle_merge(self, msg):
        if msg.dest_swarm_id == "*":
            self.broadcast(Message(MessageTypes.MERGE).to_swarm_id(self.context.hierarchy))

        self.context.go_to_next_hierarchy()
        # print(f"({msg.fid}) -> {self.context.fid} merged, new h: {self.context.hierarchy}")

    def handle_stop(self, msg):
        # if self.stop_handled:
        #     return
        # self.stop_handled = True

        # if np.random.random() < 0.5:
        self.broadcast(msg)
        # self.metrics.set_round_times(msg.args[0])
        # fin_message = Message(MessageTypes.FIN, args=(self.metrics.get_final_report(),))
        # fin_message = Message(MessageTypes.FIN)
        # self.cancel_timers()
        # final_report = self.metrics.get_final_report()
        _final_report = self.metrics.get_final_report_()
        file_name = self.context.fid

        with open(os.path.join(self.metrics.results_directory, 'json', f"{file_name:05}.json"), "w") as f:
            json.dump(_final_report, f)

        with open(os.path.join(self.metrics.results_directory, "timeline", f"timeline_{self.context.fid:05}.json"), "w") as f:
            json.dump(self.metrics.timeline, f)
        # write_json(1000+file_name, _final_report, self.metrics.results_directory)
        # self.send_to_server(fin_message)

    def compute_v(self, anchor):
        d_gtl = self.context.gtl - anchor.gtl
        d_el = self.context.el - anchor.el
        d_yaw = self.context.yaw - anchor.yaw
        # d_el_r = Rotation.from_euler('z', d_yaw, degrees=True).apply(d_el)
        # d_gtl_r = Rotation.from_euler('z', d_yaw, degrees=True).apply(d_gtl)

        # add error to position
        d_el, _ = sample_distance(d_el, np.linalg.norm(d_el))

        v = d_gtl - d_el
        d = np.linalg.norm(v)

        return v, d

    def localize_sequential_hierarchical(self):
        # if self.context.hierarchy == self.context.min_gid:
        n1 = list(filter(lambda x: self.context.min_gid in x.swarm_id, self.context.neighbors.values()))
        adjustments = np.array([[.0, .0, .0]])
        if len(n1):
            adjustments = np.vstack((adjustments, [self.compute_v(n)[0] for n in n1]))
        v = np.mean(adjustments, axis=0)
        self.context.move(v)

        # if np.random.random() > self.challenge_probability:
        #     return

        self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(self.context.min_gid))

        for fid, gid in self.context.localizer:
            if self.context.fid > fid + 1:

                # localize relative to it
                # print(self.context.fid, self.context.hierarchy)

                if self.context.hierarchy == gid:

                    if fid + 1 in self.context.neighbors:
                        # print(self.context.fid, fid+1, gid)
                        v, _ = self.compute_v(self.context.neighbors[fid + 1])
                        self.context.move(v)
                        self.broadcast(Message(MessageTypes.FOLLOW, args=(v,)).to_swarm_id(gid))
                        self.broadcast(Message(MessageTypes.MERGE).to_fls_id(fid + 1, "*"))
                        self.context.go_to_next_hierarchy()
                        # break
            # send your location
            self.broadcast(Message(MessageTypes.GOSSIP).to_fls_id(fid + 1, "*"))

    def localize_spanning(self):
        n1 = list(filter(lambda x: self.context.min_gid == x.swarm_id, self.context.neighbors.values()))
        adjustments = np.array([[.0, .0, .0]])
        if len(n1):
            adjustments = np.vstack((adjustments, [self.compute_v(n)[0] for n in n1]))
        v = np.mean(adjustments, axis=0)
        self.context.move(v)

        # if np.random.random() > self.challenge_probability:
        #     return

        self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(self.context.min_gid))

        for fid, gid in self.context.localizer:
            # localize relative to it
            # print(self.context.fid, self.context.hierarchy)
            if fid + 1 in self.context.neighbors:
                if self.context.swarm_id > self.context.neighbors[fid+1].swarm_id:
                    # print(self.context.fid, fid+1, gid)
                    v, _ = self.compute_v(self.context.neighbors[fid + 1])
                    self.context.move(v)
                    self.broadcast(Message(MessageTypes.FOLLOW, args=(v,)).to_swarm_id(gid))
            # send your location
            self.broadcast(Message(MessageTypes.GOSSIP).to_fls_id(fid + 1, "*"))

    # v0 drifts
    # def localize_spanning_2(self):
    #     # print(self.context.localizer)
    #     if Config.MULTIPLE_ANCHORS:
    #         # if self.context.intra_localizer is not None:
    #         if Config.GROUP_TYPE == 'spanning_2':
    #             n1 = list(filter(lambda x: self.context.min_gid == x.swarm_id, self.context.neighbors.values()))
    #         else:
    #             n1 = list(filter(lambda x: self.context.min_gid in x.swarm_id, self.context.neighbors.values()))
    #         adjustments = np.array([[.0, .0, .0]])
    #         if len(n1):
    #             adjustments = np.vstack((adjustments, [self.compute_v(n)[0] for n in n1]))
    #         v = np.mean(adjustments, axis=0)
    #         self.context.move(v)
    #     else:
    #         if self.context.intra_localizer in self.context.neighbors:
    #             # print(f"intra {self.context.fid} {self.context.intra_localizer} ({self.context.swarm_id})")
    #             v, _ = self.compute_v(self.context.neighbors[self.context.intra_localizer])
    #             self.context.move(v)
    #
    #     self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(self.context.min_gid))
    #
    #     # if time.time() - self.start_time > 10:
    #     for fid, gid in self.context.localizer:
    #         # localize relative to it
    #         # print(self.context.fid, fid, gid, self.context.swarm_id)
    #         if gid is not None and fid in self.context.neighbors:
    #             # print(fid, gid)
    #             # if self.context.swarm_id > self.context.neighbors[fid].swarm_id:
    #                 # print(f"inter: {self.context.fid} -> {fid} ({gid})")
    #             v, _ = self.compute_v(self.context.neighbors[fid])
    #             self.context.move(v)
    #             self.broadcast(Message(MessageTypes.FOLLOW, args=(v,)).to_swarm_id(gid))
    #         # send your location
    #         self.broadcast(Message(MessageTypes.GOSSIP).to_fls_id(fid, "*"))

    # v1 aws 1 - 4 results
    def localize_spanning_2(self):
        if not self.waiting_mode:
            n1 = list(filter(lambda x: self.context.min_gid == x.swarm_id, self.context.neighbors.values()))

            adjustments = np.array([[.0, .0, .0]])
            if len(n1):
                adjustments = np.vstack((adjustments, [self.compute_v(n)[0] for n in n1]))
                v = np.mean(adjustments, axis=0)
                if np.linalg.norm(v) > 1e-6:
                    self.context.move(v)
                else:
                    self.waiting_mode = True
            self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(self.context.min_gid))
        else:
            # print(f"{self.context.fid}_waiting")
            # pass
            for fid, gid in self.context.localizer:
                # print(self.context.fid, fid, gid, self.context.swarm_id)
                if gid is not None and fid in self.context.neighbors:
                    # print(fid, gid)
                    # if self.context.swarm_id > self.context.neighbors[fid].swarm_id:
                        # print(f"inter: {self.context.fid} -> {fid} ({gid})")
                    v, _ = self.compute_v(self.context.neighbors[fid])
                    self.context.move(v)
                    self.num_localizations += 1
                    stop = self.num_localizations == 3
                    self.broadcast(Message(MessageTypes.FOLLOW, args=(v, stop)).to_swarm_id(gid))
                    if stop:
                        self.num_localizations = 0
                        self.waiting_mode = False
                # send your location
                self.broadcast(Message(MessageTypes.GOSSIP).to_fls_id(fid, "*"))

    #v2 in-order inter-group localization
    def localize_spanning_2_variant_2(self):
        if not self.waiting_mode:
            n1 = list(filter(lambda x: self.context.min_gid == x.swarm_id, self.context.neighbors.values()))

            adjustments = np.array([[.0, .0, .0]])
            if len(n1):
                adjustments = np.vstack((adjustments, [self.compute_v(n)[0] for n in n1]))
                v = np.mean(adjustments, axis=0)
                if np.linalg.norm(v) > 1e-6:
                    self.context.move(v)
                else:
                    self.waiting_mode = True
            self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(self.context.min_gid))
        elif self.notified or self.context.min_gid == 0:
            for fid, gid in self.context.localizer:
                # print(self.context.fid, fid, gid, self.context.swarm_id)
                if gid is not None and fid in self.context.neighbors:
                    # primary localizing
                    v, _ = self.compute_v(self.context.neighbors[fid])
                    self.context.move(v)
                    self.num_localizations += 1
                    stop = self.num_localizations == 1
                    self.broadcast(Message(MessageTypes.FOLLOW, args=(v, stop)).to_swarm_id(gid))
                    if stop:
                        self.num_localizations = 0
                        self.waiting_mode = False
                        self.notified = False
                        self.context.neighbors = {}
                else:
                    # anchor
                    self.broadcast(Message(MessageTypes.NOTIFY).to_fls_id(fid, "*"))
                    # print(f"{self.context.fid} notified {fid}")

    # v3 in-order inter-group and intra-group localization
    def localize_spanning_2_variant_3(self):
        if not self.waiting_mode:
            if self.context.intra_localizer is None:
                self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(self.context.min_gid))
                self.waiting_mode = True
            elif self.context.intra_localizer in self.context.neighbors:
                v, _ = self.compute_v(self.context.neighbors[self.context.intra_localizer])
                self.context.move(v)
                self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(self.context.min_gid))
                self.context.neighbors = {}
                self.waiting_mode = True

        elif self.notified or self.context.min_gid == 0:
            for fid, gid in self.context.localizer:
                # print(self.context.fid, fid, gid, self.context.swarm_id)
                if gid is not None and fid in self.context.neighbors:
                    # primary localizing
                    v, _ = self.compute_v(self.context.neighbors[fid])
                    self.context.move(v)
                    self.num_localizations += 1
                    stop = self.num_localizations == 1
                    self.broadcast(Message(MessageTypes.FOLLOW, args=(v, stop)).to_swarm_id(gid))
                    if stop:
                        self.num_localizations = 0
                        self.waiting_mode = False
                        self.notified = False
                        self.context.neighbors = {}
                    # print(f"{self.context.fid}->{fid} ({self.context.min_gid})")

                else:
                    # anchor
                    self.broadcast(Message(MessageTypes.NOTIFY).to_fls_id(fid, "*"))
                    # print(f"{self.context.fid} notified {fid}")
            if self.context.min_gid == 0:
                self.waiting_mode = False

    def localize_mst(self):
        # localize
        if self.context.localizer in self.context.neighbors:
            v, d = self.compute_v(self.context.neighbors[self.context.localizer])
            if d > 0:
                self.context.move(v)
                for fid in self.context.anchor_for:
                    self.broadcast(Message(MessageTypes.FOLLOW, args=(v,)).to_fls_id(fid, '*'))

        # send data to anchor
        for fid in self.context.anchor_for:
            self.broadcast(Message(MessageTypes.GOSSIP).to_fls_id(fid, "*"))

    def localize_universal(self):
        # localize
        adjustments = np.array([[.0, .0, .0]])
        neighbors = self.context.neighbors.values()
        if len(neighbors):
            adjustments = np.vstack((adjustments, [self.compute_v(n)[0] for n in neighbors]))
            v = np.mean(adjustments, axis=0)
            self.context.move(v)
        self.broadcast(Message(MessageTypes.GOSSIP).to_all())

        # send data to anchor
        # for fid in self.context.anchor_for:
        #     self.broadcast(Message(MessageTypes.GOSSIP).to_fls_id(fid, "*"))


    def localize_hierarchical(self):
        n1 = list(filter(lambda x: self.context.min_gid in x.swarm_id, self.context.neighbors.values()))
        adjustments = np.array([[.0, .0, .0]])
        if len(n1):
            adjustments = np.vstack((adjustments, [self.compute_v(n) for n in n1]))
        v = np.mean(adjustments, axis=0)
        self.context.move(v)

        # if np.random.random() > self.challenge_probability:
        #     return

        self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(self.context.min_gid))

        # print(self.context.fid, self.context.swarm_id, self.context.localizer)
        for fid, gid in self.context.localizer:
            self.broadcast(Message(MessageTypes.GOSSIP).to_fls_id(fid + 1, "*"))
            if fid + 1 in self.context.neighbors:
                # print(f"{self.context.fid} localizing to {fid + 1} in group {gid}")
                v = self.compute_v(self.context.neighbors[fid + 1])/2
                self.context.move(v)
                self.broadcast(Message(MessageTypes.FOLLOW, args=(v,)).to_swarm_id(gid))

    def localize_overlapping(self):
        for gid in self.context.swarm_id:
            # print(self.context.fid, gid, self.context.neighbors.values())
            n1 = list(filter(lambda x: gid in x.swarm_id, self.context.neighbors.values()))
            adjustments = np.array([[.0, .0, .0]])
            if len(n1):
                adjustments = np.vstack((adjustments, [self.compute_v(n) for n in n1]))
            v = np.mean(adjustments, axis=0)
            self.context.move(v)

            # if np.random.random() > self.challenge_probability:
            #     return

            self.broadcast(Message(MessageTypes.GOSSIP).to_swarm_id(gid))

    def enter_available_state(self):
        # print(self.context.neighbors.values())
        # if self.context.fid % 5 == 1:
        #     n2 = list(filter(lambda x: x.fid % 5 == 1, self.context.neighbors.values()))
        #     adjustments = np.array([[.0, .0, .0]])
        #     if len(n2) == 4:
        #         adjustments = np.vstack((adjustments, [self.compute_v(n) for n in n2]))
        #
        #     v = np.mean(adjustments, axis=0)
        #     self.broadcast(Message(MessageTypes.FOLLOW, args=(v,)).to_div(5, (self.context.fid - 1) // 5))
        #     self.context.move(v)
        #     self.broadcast(Message(MessageTypes.GOSSIP).to_mod(5, 1))

        # overlapping
        n2 = list(filter(lambda x: (x.fid + 1) // 5 == (self.context.fid + 1) // 5, self.context.neighbors.values()))
        adjustments = np.array([[.0, .0, .0]])
        if len(n2) == 4:
            adjustments = np.vstack((adjustments, [self.compute_v(n) for n in n2]))

        v = np.mean(adjustments, axis=0)
        # self.broadcast(Message(MessageTypes.FOLLOW, args=(v,)).to_div(5, (self.context.fid + 1) // 5))
        self.context.move(v)
        self.broadcast(Message(MessageTypes.GOSSIP).to_div(5, (self.context.fid + 1) // 5))

        n1 = list(filter(lambda x: (x.fid - 1) // 5 == (self.context.fid - 1) // 5, self.context.neighbors.values()))
        adjustments = np.array([[.0, .0, .0]])
        if len(n1) == 4:
            adjustments = np.vstack((adjustments, [self.compute_v(n) for n in n1]))

        v = np.mean(adjustments, axis=0)
        # print(v)

        self.context.move(v)

        # if np.random.random() > self.challenge_probability:
        #     return

        challenge_msg = Message(MessageTypes.GOSSIP).to_div(5, (self.context.fid - 1) // 5)
        self.broadcast(challenge_msg)

    def fail(self):
        # print("failed")
        self.should_fail = False
        self.enter(StateTypes.DEPLOYING)
        self.context.fail()
        self.start()

    def put_state_in_q(self, event):
        msg = Message(event).to_fls(self.context)
        item = PrioritizedItem(1, time.time(), msg, False)
        self.event_queue.put(item)

    def enter(self, state, arg={}):
        self.state = state

        # if self.state == StateTypes.AVAILABLE:
        self.localize()

    def reenter_available_state(self):
        self.enter(StateTypes.AVAILABLE)

    def drive(self, msg):
        if self.should_fail:
            self.fail()

        event = msg.type
        self.context.update_neighbor(msg)

        if event == MessageTypes.STOP:
            self.handle_stop(msg)
        else:
            if event == MessageTypes.FOLLOW:
                self.handle_follow(msg)
                self.enter(StateTypes.AVAILABLE)

            elif event == MessageTypes.MERGE:
                self.handle_merge(msg)
                self.enter(StateTypes.AVAILABLE)
            elif event == MessageTypes.NOTIFY:
                self.notified = True
        # elif event == MessageTypes.SET_AVAILABLE_INTERNAL:
        #     self.reenter_available_state()

    def broadcast(self, msg):
        msg.from_fls(self.context)
        length = self.sock.broadcast(msg)
        self.context.log_sent_message(msg.type, length)

    def send_to_server(self, msg):
        msg.from_fls(self.context).to_server()
        self.sock.send_to_server(msg)


if __name__ == '__main__':
    vec = np.array([1, 0, 1])
    d = np.linalg.norm(vec)

    print(sample_distance(vec, d))
