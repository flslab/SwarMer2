import random
import uuid

from message import Message, MessageTypes
from .types import StateTypes


class StateMachine:
    def __init__(self, context, sock):
        self.state = StateTypes.AVAILABLE
        self.context = context
        self.sock = sock

    def start(self):
        self.enter(StateTypes.AVAILABLE)

    def handle_size_query(self, msg):
        resp = Message(MessageTypes.SIZE_REPLY, args=msg.args).to_fls(msg)
        self.broadcast(resp)

    def handle_size_reply(self, msg):
        if msg.args[0] == self.context.query_id:
            self.context.size += 1
            print("size_reply", self.context.fid, msg.fid, self.context.size)
        if self.context.size == self.context.count:
            print("done", self.context.fid, self.context.size)
            fin_message = Message(MessageTypes.FIN)
            self.send_to_server(fin_message)

    def handle_challenge_init(self, msg):
        if msg.swarm_id > self.context.swarm_id:
            challenge_accept_message = Message(MessageTypes.CHALLENGE_ACCEPT).to_fls(msg)
            self.broadcast(challenge_accept_message)

    def handle_challenge_accept(self, msg):
        challenge_ack_message = Message(MessageTypes.CHALLENGE_ACK).to_fls(msg)
        self.broadcast(challenge_ack_message)
        self.context.anchor = msg
        self.enter(StateTypes.BUSY_LOCALIZING)

    def handle_challenge_ack(self, msg):
        self.enter(StateTypes.BUSY_ANCHOR)

    def handle_challenge_fin(self, msg):
        self.enter(StateTypes.AVAILABLE)

    def handle_merge(self, msg):
        self.context.swarm_id = msg.swarm_id
        self.enter(StateTypes.AVAILABLE)

    def handle_follow(self, msg):
        self.context.el += msg.args(0,)
        self.enter(StateTypes.AVAILABLE)

    def handle_follow_merge(self, msg):
        self.context.swarm_id = msg.swarm_id
        self.context.el += msg.args(0, )
        self.enter(StateTypes.AVAILABLE)

    def enter_available_state(self):
        if self.context.fid % 10 == 1:
            # print("size_query", self.context.fid)
            self.context.size = 1
            self.context.query_id = uuid.uuid4()
            size_query = Message(MessageTypes.SIZE_QUERY, args=(self.context.query_id,)).to_swarm(self.context)
            self.broadcast(size_query)

        challenge_msg = Message(MessageTypes.CHALLENGE_INIT).to_all()
        self.broadcast(challenge_msg)

    def enter_busy_localizing_state(self):
        waiting_message = Message(MessageTypes.SET_WAITING).to_swarm(self.context)
        self.broadcast(waiting_message)

        d_gtl = self.context.gtl - self.context.anchor.gtl
        d_el = self.context.el - self.context.anchor.el
        v = d_gtl - d_el
        # v = self.context.gtl - self.context.el

        follow_merge_message = Message(MessageTypes.MERGE, args=(v,)).to_swarm(self.context)
        self.broadcast(follow_merge_message)
        self.context.el += v
        self.context.swarm_id = self.context.anchor.swarm_id

        challenge_fin_message = Message(MessageTypes.CHALLENGE_FIN).to_fls(self.context.anchor)
        self.broadcast(challenge_fin_message)

        self.enter(StateTypes.AVAILABLE)

    def enter_busy_anchor_state(self):
        waiting_message = Message(MessageTypes.SET_WAITING).to_swarm(self.context)
        self.broadcast(waiting_message)

        # self.context.el = self.context.gtl

    def enter_waiting_state(self):
        pass

    def enter(self, state):
        self.state = state
        print(self.context.fid, state)

        if self.state == StateTypes.AVAILABLE:
            self.enter_available_state()
        elif self.state == StateTypes.BUSY_LOCALIZING:
            self.enter_busy_localizing_state()
        elif self.state == StateTypes.BUSY_ANCHOR:
            self.enter_busy_anchor_state()
        elif self.state == StateTypes.WAITING:
            self.enter_waiting_state()

    def drive(self, msg):
        event = msg.type
        if self.state == StateTypes.AVAILABLE:
            if event == MessageTypes.CHALLENGE_INIT:
                self.handle_challenge_init(msg)
            elif event == MessageTypes.CHALLENGE_ACCEPT:
                self.handle_challenge_accept(msg)
            elif event == MessageTypes.CHALLENGE_ACK:
                self.handle_challenge_ack(msg)
            elif event == MessageTypes.SIZE_QUERY:
                self.handle_size_query(msg)
            elif event == MessageTypes.SIZE_REPLY:
                self.handle_size_reply(msg)
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
            elif event == MessageTypes.SIZE_QUERY:
                self.handle_size_query(msg)
            elif event == MessageTypes.SIZE_REPLY:
                self.handle_size_reply(msg)

        if event == MessageTypes.STOP:
            fin_message = Message(MessageTypes.FIN)
            self.send_to_server(fin_message)

    def broadcast(self, msg):
        msg.from_fls(self.context)
        self.sock.broadcast(msg)

    def send_to_server(self, msg):
        msg.from_fls(self.context).to_server()
        self.sock.send_to_server(msg)
