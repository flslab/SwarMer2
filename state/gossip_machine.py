import json
import os
import random
import time

import numpy as np
import threading
import uuid


from message import Message, MessageTypes
from config import Config
from utils import logger
from worker.network import PrioritizedItem
from .types import StateTypes


class GossipStateMachine:
    def __init__(self, context, sock, metrics, event_queue):
        self.timer_gossip = None
        self.discovered_local_state = dict()
        self.discovered_global_swarms = set()
        self.last_challenge_init = 0
        self.last_challenge_accept = 0
        self.state = StateTypes.DEPLOYING
        self.context = context
        self.metrics = metrics
        self.sock = sock
        self.timer_available = None
        self.timer_size = None
        self.timer_lease = None
        self.timer_failure = None
        self.timer_round = None
        self.challenge_ack = False
        self.challenge_probability = Config.INITIAL_CHALLENGE_PROB
        self.stop_handled = False
        self.waiting_for = None
        self.should_fail = False
        self.event_queue = event_queue
        self.thaw_ids = dict()
        self.potential_anchors = []

    def start(self):
        self.context.deploy()
        # self.enter(StateTypes.AVAILABLE)
        self.send_gossip()
        self.start_timers()

    def handle_size_query(self, msg):
        resp = Message(MessageTypes.SIZE_REPLY, args=msg.args).to_fls(msg)
        self.broadcast(resp)

    def handle_size_reply(self, msg):
        if msg.args[0] == self.context.query_id:
            self.context.size += 1
            logger.critical(f"swarm {self.context.swarm_id} size {self.context.size}")
        if self.context.size == self.context.count:
            print("__swarm__ all merged into one swarm")
            if Config.THAW_SWARMS:
                thaw_message = Message(MessageTypes.THAW_SWARM).to_all()
                self.broadcast(thaw_message)
                print(f"thaw {self.context.fid}")
                self.handle_thaw_swarm(None)
            else:
                fin_message = Message(MessageTypes.FIN)
                self.send_to_server(fin_message)

    def handle_challenge_init(self, msg):
        if time.time() - self.last_challenge_accept < Config.CHALLENGE_ACCEPT_DURATION:
            return
        if msg.swarm_id != self.context.swarm_id:
            self.last_challenge_accept = time.time()
            challenge_accept_message = Message(MessageTypes.CHALLENGE_ACCEPT, args=msg.args).to_fls(msg)
            self.broadcast(challenge_accept_message)
            if msg.swarm_id < self.context.swarm_id:
                self.potential_anchors.append(msg)

    def handle_challenge_accept(self, msg):
        if msg.args[0] == self.context.challenge_id:
            self.challenge_ack = True
            self.context.set_challenge_id(None)
            challenge_ack_message = Message(MessageTypes.CHALLENGE_ACK).to_fls(msg)
            self.broadcast(challenge_ack_message)
            self.cancel_lease_of_potential_anchors(msg)
            if msg.swarm_id < self.context.swarm_id:
                # if msg.fid == 1:
                self.enter(StateTypes.BUSY_LOCALIZING, msg)
            else:
                # if self.context.fid == 1:
                self.context.grant_lease(msg.fid)
                self.enter(StateTypes.BUSY_ANCHOR)

    def handle_challenge_ack(self, msg):
        self.cancel_lease_of_potential_anchors(msg)
        if msg.swarm_id < self.context.swarm_id:
            # if msg.fid == 1:
            self.enter(StateTypes.BUSY_LOCALIZING, msg)
        else:
            # if self.context.fid == 1:
            self.context.grant_lease(msg.fid)
            self.enter(StateTypes.BUSY_ANCHOR)

    def cancel_lease_of_potential_anchors(self, msg):
        # print([p.fid for p in self.potential_anchors])
        for pa in self.potential_anchors:
            if pa.fid != msg.fid:
                self.broadcast(Message(MessageTypes.LEASE_CANCEL).to_fls(pa))
        self.potential_anchors = []

    def handle_cancel_lease(self, msg):
        # print(f"cancel {msg.fid}")
        self.context.cancel_lease(msg.fid)
        if self.context.is_lease_empty():
            self.enter(StateTypes.AVAILABLE)

    def handle_challenge_fin(self, msg):
        self.context.release_lease(msg.fid)
        if self.context.is_lease_empty():
            self.enter(StateTypes.AVAILABLE)

    def handle_merge(self, msg):
        self.context.set_swarm_id(msg.swarm_id)
        # self.enter(StateTypes.AVAILABLE)

    def handle_follow(self, msg):
        self.context.move(msg.args[0])
        self.enter(StateTypes.AVAILABLE)

    def handle_follow_merge(self, msg):
        self.context.move(msg.args[0])
        self.context.set_swarm_id(msg.args[1])
        self.challenge_probability /= Config.CHALLENGE_PROB_DECAY
        self.enter(StateTypes.AVAILABLE)

    def handle_thaw_swarm(self, msg):
        t = msg.args[0]
        if t in self.thaw_ids:
            return

        self.thaw_ids[t] = True
        # if np.random.random() < 0.5:
        #     self.broadcast(msg)
        self.enter(StateTypes.DEPLOYING)
        # print(f"{self.context.fid} thawed")
        self.challenge_ack = False
        self.cancel_timers()
        self.context.thaw_swarm()
        self.challenge_probability = 1
        self.send_gossip()

        # time.sleep(1)
        # self.enter(StateTypes.AVAILABLE)
        # self.start_timers()

    def handle_stop(self, msg):
        if self.stop_handled:
            return
        self.stop_handled = True

        if np.random.random() < 0.5:
            self.broadcast(msg)
        # self.metrics.set_round_times(msg.args[0])
        # fin_message = Message(MessageTypes.FIN, args=(self.metrics.get_final_report(),))
        # fin_message = Message(MessageTypes.FIN)
        self.cancel_timers()
        # final_report = self.metrics.get_final_report()
        _final_report = self.metrics.get_final_report_()
        file_name = self.context.fid

        with open(os.path.join(self.metrics.results_directory, 'json', f"{file_name:05}.json"), "w") as f:
            json.dump(_final_report, f)

        with open(os.path.join(self.metrics.results_directory, f"timeline_{self.context.fid:05}.json"), "w") as f:
            json.dump(self.metrics.timeline, f)
        # write_json(1000+file_name, _final_report, self.metrics.results_directory)
        # self.send_to_server(fin_message)

    def handle_lease_renew(self, msg):
        self.context.grant_lease(msg.fid)

    def handle_set_waiting(self, msg):
        self.waiting_for = msg.args[0]
        self.enter(StateTypes.WAITING)

    def enter_available_state(self):
        # if self.context.fid % 2:
        #     return
        if time.time() - self.last_challenge_init < Config.CHALLENGE_INIT_DURATION:
            return
        # if np.random.random() < self.challenge_probability:
        if not self.challenge_ack:
            self.context.increment_range()

        self.last_challenge_init = time.time()
        self.challenge_ack = False
        self.context.set_challenge_id(str(uuid.uuid4())[:8])
        challenge_msg = Message(MessageTypes.CHALLENGE_INIT, args=(self.context.challenge_id,)).to_all()
        self.broadcast(challenge_msg)

    def enter_busy_localizing_state(self, msg):
        self.context.set_anchor(msg)
        self.set_lease_timer()
        self.context.log_localize()
        waiting_message = Message(MessageTypes.SET_WAITING, args=(StateTypes.BUSY_LOCALIZING,)).to_swarm(self.context)
        self.broadcast(waiting_message)

        if self.context.anchor is not None:
            d_gtl = self.context.gtl - self.context.anchor.gtl
            d_el = self.context.el - self.context.anchor.el
            v = d_gtl - d_el
            d = np.linalg.norm(v)
            if d >= Config.MIN_ADJUSTMENT:
                follow_merge_message = Message(MessageTypes.FOLLOW_MERGE, args=(v, self.context.anchor.swarm_id))\
                    .to_swarm(self.context)
                self.broadcast(follow_merge_message)

            if d >= Config.MIN_ADJUSTMENT:
                self.context.move(v)

            if self.context.anchor is not None:
                self.context.set_swarm_id(self.context.anchor.swarm_id)

                challenge_fin_message = Message(MessageTypes.CHALLENGE_FIN).to_fls(self.context.anchor)
                self.broadcast(challenge_fin_message)
                self.challenge_probability /= Config.CHALLENGE_PROB_DECAY

        self.enter(StateTypes.AVAILABLE)

    def enter_busy_anchor_state(self):
        self.context.log_anchor()
        waiting_message = Message(MessageTypes.SET_WAITING, args=(StateTypes.BUSY_ANCHOR,)).to_swarm(self.context)
        self.broadcast(waiting_message)

    def enter_waiting_state(self):
        pass

    def leave_busy_anchor_state(self):
        self.context.clear_lease_table()
        available_message = Message(MessageTypes.SET_AVAILABLE).to_swarm(self.context)
        self.broadcast(available_message)

    def leave_busy_localizing(self):
        if self.context.anchor:
            cancel_message = Message(MessageTypes.LEASE_CANCEL,
                                     args=(self.context.query_id,)).to_fls(self.context.anchor)
            self.broadcast(cancel_message)
        if self.timer_lease is not None:
            self.timer_lease.cancel()
            self.timer_lease = None
        self.context.set_challenge_id(None)
        self.context.set_anchor(None)

    def start_round_timer(self):
        if self.timer_round is not None:
            self.timer_round.cancel()
            self.timer_round = None

        h = np.log2(self.context.count)
        t = np.random.uniform(h, 1.5 * h)
        self.timer_round = threading.Timer(t, self.put_state_in_q, args=(MessageTypes.THAW_SWARM_INTERNAL,))
        self.timer_round.start()

    def start_failure_timer(self):
        if self.timer_failure is not None:
            self.timer_failure.cancel()
            self.timer_failure = None
        self.timer_failure = threading.Timer(Config.FAILURE_TIMEOUT, self.put_state_in_q, args=(MessageTypes.FAIL_INTERNAL,))
        self.timer_failure.start()

    def set_fail(self):
        if Config.FAILURE_PROB and np.random.random() <= Config.FAILURE_PROB:
            self.should_fail = True
        else:
            self.start_failure_timer()

    def query_size(self):
        if self.timer_size is not None:
            self.timer_size.cancel()
            self.timer_size = None

        self.timer_size = threading.Timer(Config.SIZE_QUERY_TIMEOUT, self.query_size)
        self.timer_size.start()

        if self.context.fid % int(100 / Config.SIZE_QUERY_PARTICIPATION_PERCENT) == 1:
            self.context.size = 1
            self.context.set_query_id(str(uuid.uuid4())[:8])
            size_query = Message(MessageTypes.SIZE_QUERY, args=(self.context.query_id,)).to_swarm(self.context)
            self.broadcast(size_query)

    def set_lease_timer(self):
        if self.timer_lease is not None:
            self.timer_lease.cancel()
            self.timer_lease = None

        self.timer_lease = threading.Timer(Config.CHALLENGE_LEASE_DURATION, self.put_state_in_q, args=(MessageTypes.RENEW_LEASE_INTERNAL,))
        self.timer_lease.start()

    def renew_lease(self):
        if self.state == StateTypes.BUSY_LOCALIZING and self.context.anchor:
            renew_message = Message(MessageTypes.LEASE_RENEW, args=(self.context.query_id,)).to_fls(self.context.anchor)
            self.broadcast(renew_message)
            self.set_lease_timer()

    def fail(self):
        # print("failed")
        self.should_fail = False
        self.cancel_timers()
        self.enter(StateTypes.DEPLOYING)
        self.context.fail()
        self.start()

    def put_state_in_q(self, event):
        msg = Message(event).to_fls(self.context)
        item = PrioritizedItem(1, time.time(), msg, False)
        self.event_queue.put(item)
        # print(item)

    def enter(self, state, arg={}):
        # if self.timer_available is not None:
        #     self.timer_available.cancel()
        #     self.timer_available = None

        self.leave(self.state)
        self.state = state

        if self.state == StateTypes.AVAILABLE:
            self.enter_available_state()
        elif self.state == StateTypes.BUSY_LOCALIZING:
            self.enter_busy_localizing_state(arg)
        elif self.state == StateTypes.BUSY_ANCHOR:
            self.enter_busy_anchor_state()
        elif self.state == StateTypes.WAITING:
            self.enter_waiting_state()

        # if self.state != StateTypes.BUSY_ANCHOR \
        #         and self.state != StateTypes.BUSY_LOCALIZING \
        #         and self.state != StateTypes.DEPLOYING:
        #     self.timer_available = \
        #         threading.Timer(0.1 + np.random.random() * Config.STATE_TIMEOUT, self.put_state_in_q, args=(MessageTypes.SET_AVAILABLE_INTERNAL,))
        #     self.timer_available.start()

    def reenter_available_state(self):
        if self.state != StateTypes.BUSY_ANCHOR\
                and self.state != StateTypes.BUSY_LOCALIZING\
                and self.state != StateTypes.DEPLOYING:
            self.enter(StateTypes.AVAILABLE)

    def leave(self, state):
        if state == StateTypes.BUSY_ANCHOR:
            self.leave_busy_anchor_state()
        elif state == StateTypes.BUSY_LOCALIZING:
            self.leave_busy_localizing()

    def drive(self, msg):
        # print(msg)
        if self.should_fail:
            self.fail()

        event = msg.type
        self.context.update_neighbor(msg)

        if self.state == StateTypes.AVAILABLE:
            if event == MessageTypes.CHALLENGE_INIT:
                self.handle_challenge_init(msg)
            elif event == MessageTypes.CHALLENGE_ACCEPT:
                self.handle_challenge_accept(msg)
            elif event == MessageTypes.CHALLENGE_ACK:
                self.handle_challenge_ack(msg)
            elif event == MessageTypes.SET_WAITING:
                self.handle_set_waiting(msg)

        elif self.state == StateTypes.BUSY_ANCHOR:
            if event == MessageTypes.LEASE_RENEW:
                self.handle_lease_renew(msg)
            elif event == MessageTypes.MERGE:
                self.handle_merge(msg)
            elif event == MessageTypes.CHALLENGE_FIN:
                self.handle_challenge_fin(msg)
            elif event == MessageTypes.LEASE_CANCEL:
                self.handle_cancel_lease(msg)

            self.context.refresh_lease_table()
            if self.context.is_lease_empty():
                self.enter(StateTypes.AVAILABLE)

        elif self.state == StateTypes.WAITING:
            if event == MessageTypes.FOLLOW:
                self.handle_follow(msg)
            elif event == MessageTypes.MERGE:
                self.handle_merge(msg)
            elif event == MessageTypes.FOLLOW_MERGE:
                self.handle_follow_merge(msg)
            elif event == MessageTypes.SET_AVAILABLE:
                self.enter(StateTypes.AVAILABLE)

            if self.waiting_for == StateTypes.BUSY_ANCHOR:
                if event == MessageTypes.CHALLENGE_INIT:
                    self.handle_challenge_init(msg)
                elif event == MessageTypes.CHALLENGE_ACK:
                    self.handle_challenge_ack(msg)

        if event == MessageTypes.STOP:
            self.handle_stop(msg)
        elif event == MessageTypes.SIZE_QUERY:
            self.handle_size_query(msg)
        elif event == MessageTypes.SIZE_REPLY:
            self.handle_size_reply(msg)
        elif event == MessageTypes.THAW_SWARM:
            self.handle_thaw_swarm(msg)
        elif event == MessageTypes.RENEW_LEASE_INTERNAL:
            self.renew_lease()
        elif event == MessageTypes.SET_AVAILABLE_INTERNAL:
            self.reenter_available_state()
        elif event == MessageTypes.FAIL_INTERNAL:
            self.set_fail()
        elif event == MessageTypes.THAW_SWARM_INTERNAL:
            self.handle_thaw_swarm(Message(MessageTypes.THAW_SWARM, args=(time.time(),)).from_fls(self.context).to_all())
        elif event == MessageTypes.GOSSIP_INTERNAL:
            self.send_gossip()
        elif event == MessageTypes.GOSSIP:
            self.handle_gossip(msg)
        elif event == MessageTypes.MERGE:
            self.handle_merge(msg)

    def broadcast(self, msg):
        msg.from_fls(self.context)
        length = self.sock.broadcast(msg)
        self.context.log_sent_message(msg.type, length)

    def send_to_server(self, msg):
        msg.from_fls(self.context).to_server()
        self.sock.send_to_server(msg)

    def start_timers(self):
        if Config.PROBABILISTIC_ROUND:
            self.start_round_timer()
        if Config.DECENTRALIZED_SWARM_SIZE:
            self.query_size()
        if Config.FAILURE_TIMEOUT:
            self.start_failure_timer()

    def cancel_timers(self):
        if self.timer_available is not None:
            self.timer_available.cancel()
            self.timer_available = None
        if self.timer_size is not None:
            self.timer_size.cancel()
            self.timer_size = None
        if self.timer_lease is not None:
            self.timer_lease.cancel()
            self.timer_lease = None
        if self.timer_failure is not None:
            self.timer_failure.cancel()
            self.timer_failure = None
        if self.timer_round is not None:
            self.timer_round.cancel()
            self.timer_round = None
        if self.timer_gossip is not None:
            self.timer_gossip.cancel()
            self.timer_gossip = None

    def send_gossip(self):
        number_of_swarms = len(self.discovered_global_swarms)
        if 0 < number_of_swarms <= Config.GOSSIP_SWARM_COUNT_THRESHOLD:
            arg = self.discovered_global_swarms
        else:
            arg = set()
        self.broadcast(Message(MessageTypes.GOSSIP, args=(arg,)))

        self.timer_gossip = \
            threading.Timer(Config.GOSSIP_TIMEOUT, self.put_state_in_q,
                            args=(MessageTypes.GOSSIP_INTERNAL,))
        self.timer_gossip.start()

        # print(arg)

    def handle_gossip(self, msg):
        self.update_discovered_local_state(msg)
        self.update_discovered_global_swarms()
        self.check_thaw_condition()

    def update_discovered_local_state(self, msg):
        gossip_swarms = msg.args[0]
        self.discovered_local_state[msg.fid] = (time.time(), msg.swarm_id, gossip_swarms)
        print(f"_local {self.context.fid}:{self.context.swarm_id} {self.discovered_local_state}")

    def update_discovered_global_swarms(self):
        self.discovered_global_swarms = set()
        for s in self.discovered_local_state:
            # print("_", self.discovered_local_state[s])
            self.discovered_global_swarms |= (self.discovered_local_state[s][2] | {self.discovered_local_state[s][1]})
        print(f"_global {self.context.fid}:{self.context.swarm_id} {self.discovered_global_swarms}")

    def check_thaw_condition(self):
        if len(self.discovered_global_swarms) == 1 and list(self.discovered_global_swarms)[0] == self.context.swarm_id:
            self.broadcast(Message(MessageTypes.THAW_SWARM, args=(int(time.time()),)).to_all())
            print(f"one swarm detected by {self.context.fid}")
