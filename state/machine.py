import numpy as np
import threading
import uuid


from message import Message, MessageTypes
from config import Config
from utils import logger, write_json
from .types import StateTypes


class StateMachine:
    def __init__(self, context, sock, metrics):
        self.state = StateTypes.AVAILABLE
        self.context = context
        self.metrics = metrics
        self.sock = sock
        self.timer_available = None
        self.timer_size = None
        self.timer_lease = None
        self.timer_failure = None
        self.challenge_ack = False
        self.challenge_probability = Config.INITIAL_CHALLENGE_PROB
        self.stop_handled = False
        self.waiting_for = None

    def start(self):
        self.context.deploy()
        self.enter(StateTypes.AVAILABLE)
        if Config.DECENTRALIZED_SWARM_SIZE:
            self.query_size()
        if Config.FAILURE_TIMEOUT:
            self.timer_failure = threading.Timer(Config.FAILURE_TIMEOUT * np.random.random(), self.fail)
            self.timer_failure.start()

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
        if msg.swarm_id != self.context.swarm_id:
            challenge_accept_message = Message(MessageTypes.CHALLENGE_ACCEPT, args=msg.args).to_fls(msg)
            self.broadcast(challenge_accept_message)

    def handle_challenge_accept(self, msg):
        if msg.args[0] == self.context.challenge_id:
            self.challenge_ack = True
            self.context.set_challenge_id(None)
            challenge_ack_message = Message(MessageTypes.CHALLENGE_ACK).to_fls(msg)
            self.broadcast(challenge_ack_message)
            if msg.swarm_id < self.context.swarm_id:
                self.context.set_anchor(msg)
                self.enter(StateTypes.BUSY_LOCALIZING)
            else:
                self.context.grant_lease(msg.fid)
                self.enter(StateTypes.BUSY_ANCHOR)

    def handle_challenge_ack(self, msg):
        if msg.swarm_id < self.context.swarm_id:
            self.context.set_anchor(msg)
            self.enter(StateTypes.BUSY_LOCALIZING)
        else:
            self.context.grant_lease(msg.fid)
            self.enter(StateTypes.BUSY_ANCHOR)

    def handle_cancel_lease(self, msg):
        self.context.cancel_lease(msg.fid)
        if self.context.is_lease_empty():
            self.enter(StateTypes.AVAILABLE)

    def handle_challenge_fin(self, msg):
        self.context.release_lease(msg.fid)
        if self.context.is_lease_empty():
            self.enter(StateTypes.AVAILABLE)

    def handle_merge(self, msg):
        self.context.set_swarm_id(msg.swarm_id)
        self.enter(StateTypes.AVAILABLE)

    def handle_follow(self, msg):
        self.context.move(msg.args[0])
        self.enter(StateTypes.AVAILABLE)

    def handle_follow_merge(self, msg):
        self.context.move(msg.args[0])
        self.context.set_swarm_id(msg.args[1])
        self.challenge_probability /= Config.CHALLENGE_PROB_DECAY
        self.enter(StateTypes.AVAILABLE)

    def handle_thaw_swarm(self, msg):
        self.challenge_ack = False
        self.cancel_timers()
        self.context.thaw_swarm()
        self.challenge_probability = 1
        self.enter(StateTypes.AVAILABLE)

    def handle_stop(self, msg):
        if self.stop_handled:
            return
        self.stop_handled = True
        # self.metrics.set_round_times(msg.args[0])
        # fin_message = Message(MessageTypes.FIN, args=(self.metrics.get_final_report(),))
        # fin_message = Message(MessageTypes.FIN)
        self.cancel_timers()
        # final_report = self.metrics.get_final_report()
        _final_report = self.metrics.get_final_report_()
        file_name = self.context.fid

        write_json(file_name, _final_report, self.metrics.results_directory)
        # write_json(1000+file_name, _final_report, self.metrics.results_directory)
        # self.send_to_server(fin_message)

    def handle_lease_renew(self, msg):
        self.context.grant_lease(msg.fid)

    def handle_set_waiting(self, msg):
        self.waiting_for = msg.args[0]
        self.enter(StateTypes.WAITING)

    def enter_available_state(self):
        if np.random.random() < self.challenge_probability:
            if not self.challenge_ack:
                if not self.context.increment_range():
                    return

            self.challenge_ack = False
            self.context.set_challenge_id(str(uuid.uuid4())[:8])
            challenge_msg = Message(MessageTypes.CHALLENGE_INIT, args=(self.context.challenge_id,)).to_all()
            self.broadcast(challenge_msg)

    def enter_busy_localizing_state(self):
        self.set_lease_timer()
        self.context.log_localize()
        waiting_message = Message(MessageTypes.SET_WAITING, args=(StateTypes.BUSY_LOCALIZING,)).to_swarm(self.context)
        self.broadcast(waiting_message)

        d_gtl = self.context.gtl - self.context.anchor.gtl
        d_el = self.context.el - self.context.anchor.el
        v = d_gtl - d_el

        follow_merge_message = Message(MessageTypes.FOLLOW_MERGE, args=(v, self.context.anchor.swarm_id))\
            .to_swarm(self.context)
        self.broadcast(follow_merge_message)
        self.context.move(v)

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
        cancel_message = Message(MessageTypes.LEASE_CANCEL, args=(self.context.query_id,)).to_fls(self.context.anchor)
        self.broadcast(cancel_message)
        if self.timer_lease is not None:
            self.timer_lease.cancel()
            self.timer_lease = None
        self.context.set_challenge_id(None)
        self.context.set_anchor(None)

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

        self.timer_lease = threading.Timer(Config.CHALLENGE_LEASE_DURATION, self.renew_lease)
        self.timer_lease.start()

    def renew_lease(self):
        if self.state == StateTypes.BUSY_LOCALIZING:
            renew_message = Message(MessageTypes.LEASE_RENEW, args=(self.context.query_id,)).to_fls(self.context.anchor)
            self.broadcast(renew_message)
            self.set_lease_timer()

    def fail(self):
        self.cancel_timers()
        self.enter(StateTypes.DEPLOYING)
        self.context.fail()
        self.start()

    def enter(self, state):
        if self.timer_available is not None:
            self.timer_available.cancel()
            self.timer_available = None

        self.leave(self.state)
        self.state = state

        if self.state == StateTypes.AVAILABLE:
            self.enter_available_state()
        elif self.state == StateTypes.BUSY_LOCALIZING:
            self.enter_busy_localizing_state()
        elif self.state == StateTypes.BUSY_ANCHOR:
            self.enter_busy_anchor_state()
        elif self.state == StateTypes.WAITING:
            self.enter_waiting_state()

        if self.state != StateTypes.BUSY_ANCHOR \
                and self.state != StateTypes.BUSY_LOCALIZING \
                and self.state != StateTypes.DEPLOYING:
            self.timer_available = \
                threading.Timer(0.1 + np.random.random() * Config.STATE_TIMEOUT, self.reenter, (StateTypes.AVAILABLE,))
            self.timer_available.start()

    def reenter(self, state):
        if self.state != StateTypes.BUSY_ANCHOR\
                and self.state != StateTypes.BUSY_LOCALIZING\
                and self.state != StateTypes.DEPLOYING:
            self.enter(state)

    def leave(self, state):
        if state == StateTypes.BUSY_ANCHOR:
            self.leave_busy_anchor_state()
        elif state == StateTypes.BUSY_LOCALIZING:
            self.leave_busy_localizing()

    def drive(self, msg):
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

        elif self.state == StateTypes.BUSY_LOCALIZING:
            if event == MessageTypes.LEASE_GRANT:
                pass

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

    def broadcast(self, msg):
        msg.from_fls(self.context)
        length = self.sock.broadcast(msg)
        self.context.log_sent_message(msg.type, length)

    def send_to_server(self, msg):
        msg.from_fls(self.context).to_server()
        self.sock.send_to_server(msg)

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
