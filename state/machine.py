import random
import threading
import uuid

from message import Message, MessageTypes
from config import Config
from utils import logger
from .types import StateTypes


class StateMachine:
    def __init__(self, context, sock, barrier):
        self.state = StateTypes.AVAILABLE
        self.context = context
        self.sock = sock
        self.barrier = barrier
        self.timer_available = None
        self.timer_size = None
        self.challenge_ack = False
        self.challenge_probability = 1

    def start(self):
        self.context.deploy()
        self.enter(StateTypes.AVAILABLE)
        self.query_size()

    def handle_size_query(self, msg):
        resp = Message(MessageTypes.SIZE_REPLY, args=msg.args).to_fls(msg)
        self.broadcast(resp)

    def handle_size_reply(self, msg):
        if msg.args[0] == self.context.query_id:
            self.context.size += 1
            logger.critical(f"swarm {self.context.swarm_id} size {self.context.size}")
        if self.context.size == self.context.count:
            if Config.THAW_SWARMS:
                thaw_message = Message(MessageTypes.THAW_SWARM).to_all()
                self.broadcast(thaw_message)
                print(f"thaw {self.context.fid}")
                self.handle_thaw_swarm(None)
            else:
                fin_message = Message(MessageTypes.FIN)
                self.send_to_server(fin_message)

    def handle_challenge_init(self, msg):
        logger.info(f"{self.context.fid} received challenge message from {msg.fid}")
        if msg.swarm_id != self.context.swarm_id:
            challenge_accept_message = Message(MessageTypes.CHALLENGE_ACCEPT, args=msg.args).to_fls(msg)
            self.broadcast(challenge_accept_message)
            logger.info(f"{self.context.fid} sent challenge accept to {msg.fid}")

    def handle_challenge_accept(self, msg):
        logger.info(f"{self.context.fid} received challenge accept from {msg.fid}")
        if msg.args[0] == self.context.challenge_id:
            logger.info(f"{self.context.fid} challenge id matches")
            self.challenge_ack = True
            self.context.set_challenge_id(None)
            challenge_ack_message = Message(MessageTypes.CHALLENGE_ACK).to_fls(msg)
            self.broadcast(challenge_ack_message)
            if msg.swarm_id < self.context.swarm_id:
                self.context.set_anchor(msg)
                self.enter(StateTypes.BUSY_LOCALIZING)
            else:
                self.enter(StateTypes.BUSY_ANCHOR)

        else:
            logger.info(f"{self.context.fid} challenge id does not match")

    def handle_challenge_ack(self, msg):
        if msg.swarm_id < self.context.swarm_id:
            self.context.set_anchor(msg)
            self.enter(StateTypes.BUSY_LOCALIZING)
        else:
            self.enter(StateTypes.BUSY_ANCHOR)

    def handle_challenge_fin(self, msg):
        self.enter(StateTypes.AVAILABLE)
        available_message = Message(MessageTypes.SET_AVAILABLE).to_swarm(self.context)
        self.broadcast(available_message)

    def handle_merge(self, msg):
        self.context.set_swarm_id(msg.swarm_id)
        self.enter(StateTypes.AVAILABLE)

    def handle_follow(self, msg):
        self.context.move(msg.args[0])
        self.enter(StateTypes.AVAILABLE)

    def handle_follow_merge(self, msg):
        print(f"{self.context.fid}({self.context.swarm_id}) merged into {msg.args[1]}")
        self.context.move(msg.args[0])
        self.context.set_swarm_id(msg.args[1])
        self.challenge_probability /= Config.CHALLENGE_REQUEST_DECAY
        self.enter(StateTypes.AVAILABLE)

    def handle_thaw_swarm(self, msg):
        # self.handle_report(None)
        self.context.thaw_swarm()
        self.enter(StateTypes.AVAILABLE)
        logger.critical(f"{self.context.fid} thawed")

    def handle_stop(self, msg):
        fin_message = Message(MessageTypes.FIN, args=(self.get_final_report(),))
        self.cancel_timers()
        self.send_to_server(fin_message)

    def handle_report(self, msg):
        report_message = Message(MessageTypes.REPORT, args=(self.get_final_report(),))
        self.cancel_timers()
        self.send_to_server(report_message)

    def enter_available_state(self):
        print(f"fid: {self.context.fid} swarm: {self.context.swarm_id}")

        if random.random() < self.challenge_probability:
            if not self.challenge_ack:
                if not self.context.increment_range():
                    return

            self.challenge_ack = False
            self.context.set_challenge_id(str(uuid.uuid4())[:8])
            challenge_msg = Message(MessageTypes.CHALLENGE_INIT, args=(self.context.challenge_id,)).to_all()
            self.broadcast(challenge_msg)
            logger.info(f"{self.context.fid} sent challenge request")

        # print(self.context.history.merge_lists())
        # n_waiting = self.barrier.wait()
        # print(n_waiting)

    def enter_busy_localizing_state(self):
        logger.info(f"{self.context.fid} localizing relative to {self.context.anchor.fid}")
        waiting_message = Message(MessageTypes.SET_WAITING).to_swarm(self.context)
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
        self.challenge_probability /= Config.CHALLENGE_REQUEST_DECAY

        self.enter(StateTypes.AVAILABLE)

    def enter_busy_anchor_state(self):
        waiting_message = Message(MessageTypes.SET_WAITING).to_swarm(self.context)
        self.broadcast(waiting_message)
        # self.challenge_probability /= Config.CHALLENGE_REQUEST_DECAY

    def enter_waiting_state(self):
        pass

    def query_size(self):
        if self.timer_size is not None:
            self.timer_size.cancel()
            self.timer_size = None

        self.timer_size = threading.Timer(Config.SIZE_QUERY_TIMEOUT, self.query_size)
        self.timer_size.start()

        if self.context.fid % 2:
            self.context.size = 1
            self.context.set_query_id(str(uuid.uuid4())[:8])
            size_query = Message(MessageTypes.SIZE_QUERY, args=(self.context.query_id,)).to_swarm(self.context)
            self.broadcast(size_query)

    def enter(self, state):
        self.state = state

        if self.timer_available is not None:
            self.timer_available.cancel()
            self.timer_available = None

        self.timer_available = threading.Timer(Config.STATE_TIMEOUT, self.reenter, (StateTypes.AVAILABLE,))
        self.timer_available.start()

        if self.state == StateTypes.AVAILABLE:
            self.enter_available_state()
        elif self.state == StateTypes.BUSY_LOCALIZING:
            self.enter_busy_localizing_state()
        elif self.state == StateTypes.BUSY_ANCHOR:
            self.enter_busy_anchor_state()
        elif self.state == StateTypes.WAITING:
            self.enter_waiting_state()

    def reenter(self, state):
        self.enter(state)

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
                self.enter(StateTypes.WAITING)

        elif self.state == StateTypes.BUSY_LOCALIZING:
            if event == MessageTypes.LEASE_GRANT:
                pass

        elif self.state == StateTypes.BUSY_ANCHOR:
            if event == MessageTypes.LEASE_RENEW:
                pass
            elif event == MessageTypes.MERGE:
                self.handle_merge(msg)
            elif event == MessageTypes.CHALLENGE_FIN:
                self.handle_challenge_fin(msg)

        elif self.state == StateTypes.WAITING:
            if event == MessageTypes.FOLLOW:
                self.handle_follow(msg)
            elif event == MessageTypes.MERGE:
                self.handle_merge(msg)
            elif event == MessageTypes.FOLLOW_MERGE:
                self.handle_follow_merge(msg)
            elif event == MessageTypes.SET_AVAILABLE:
                self.enter(StateTypes.AVAILABLE)
            elif event == MessageTypes.CHALLENGE_INIT:
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
        elif event == MessageTypes.REPORT:
            self.handle_report(msg)

    def get_final_report(self):
        report = {
            "bytes_sent": sum([s.meta["length"] for s in self.context.get_sent_messages()]),
            "bytes_received": sum([r.meta["length"] for r in self.context.get_received_messages()])
        }
        return report

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
