import time
import message
from .types import StateTypes


class StateMachine:
    def __init__(self, context, sock):
        self.state = StateTypes.AVAILABLE
        self.context = context
        self.sock = sock
        self.size = 1
        self.anchor = None

    def start(self):
        self.enter(StateTypes.AVAILABLE)

    def handle_size_query(self, msg):
        resp = message.Message(message.MessageTypes.SIZE_REPLY).from_fls(self.context).to_fls(msg)
        self.sock.broadcast(resp)

    def handle_size_reply(self, msg):
        if msg.swarm_id == self.context.swarm_id:
            self.size += 1
        if self.size == self.context.count:
            stop_msg = message.Message(message.MessageTypes.STOP).from_server().to_all()
            self.sock.broadcast(stop_msg)

    def handle_challenge_init(self, msg):
        if msg.swarm_id > self.context.swarm_id:
            challenge_accept_message = message.Message(message.MessageTypes.CHALLENGE_ACCEPT) \
                .from_fls(self.context).to_fls(msg)
            self.sock.broadcast(challenge_accept_message)

    def handle_challenge_accept(self, msg):
        challenge_ack_message = message.Message(message.MessageTypes.CHALLENGE_ACK) \
            .from_fls(self.context).to_fls(msg)
        self.sock.broadcast(challenge_ack_message)
        self.anchor = msg
        self.enter(StateTypes.BUSY_LOCALIZING)

    def handle_challenge_ack(self, msg):
        self.enter(StateTypes.BUSY_ANCHOR)

    def handle_challenge_fin(self, msg):
        self.enter(StateTypes.AVAILABLE)

    def handle_merge(self, msg):
        self.context.swarm_id = msg.swarm_id

    def handle_follow(self, msg):
        self.context.el += msg.args(0,)

    def handle_follow_merge(self, msg):
        self.context.swarm_id = msg.swarm_id
        self.context.el += msg.args(0, )

    def enter_available_state(self):
        # if self.context.fid == 1:
        self.size = 1
        size_query = message.Message(message.MessageTypes.SIZE_QUERY).from_fls(self.context).to_swarm(self.context)
        self.sock.broadcast(size_query)

        challenge_msg = message.Message(message.MessageTypes.CHALLENGE_INIT).from_fls(self.context).to_all()
        self.sock.broadcast(challenge_msg)

    def enter_busy_localizing_state(self):
        waiting_message = message.Message(message.MessageTypes.SET_WAITING)\
            .from_fls(self.context).to_swarm(self.context)
        self.sock.broadcast(waiting_message)

        d_gtl = self.context.gtl - self.anchor.gtl
        d_el = self.context.el - self.anchor.el
        v = d_gtl - d_el

        follow_merge_message = message.Message(message.MessageTypes.MERGE, args=(v,))\
            .from_fls(self.context).to_swarm(self.context)
        self.sock.broadcast(follow_merge_message)
        self.context.el += v
        self.context.swarm_id = self.anchor.swarm_id

        challenge_fin_message = message.Message(message.MessageTypes.CHALLENGE_FIN)\
            .from_fls(self.context).to_fls(self.anchor)
        self.sock.broadcast(challenge_fin_message)

        self.enter(StateTypes.AVAILABLE)

    def enter_busy_anchor_state(self):
        waiting_message = message.Message(message.MessageTypes.SET_WAITING) \
            .from_fls(self.context).to_swarm(self.context)
        self.sock.broadcast(waiting_message)

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
            if event == message.MessageTypes.CHALLENGE_INIT:
                self.handle_challenge_init(msg)
            elif event == message.MessageTypes.CHALLENGE_ACCEPT:
                self.handle_challenge_accept(msg)
            elif event == message.MessageTypes.CHALLENGE_ACK:
                self.handle_challenge_ack(msg)
            elif event == message.MessageTypes.SIZE_QUERY:
                self.handle_size_query(msg)
            elif event == message.MessageTypes.SIZE_REPLY:
                self.handle_size_reply(msg)
            elif event == message.MessageTypes.SET_WAITING:
                self.enter(StateTypes.WAITING)

        elif self.state == StateTypes.BUSY_LOCALIZING:
            if event == message.MessageTypes.LEASE_GRANT:
                pass

        elif self.state == StateTypes.BUSY_ANCHOR:
            if event == message.MessageTypes.LEASE_RENEW:
                pass
            elif event == message.MessageTypes.MERGE:
                self.handle_merge(msg)
            elif event == message.MessageTypes.CHALLENGE_FIN:
                self.handle_challenge_fin(msg)

        elif self.state == StateTypes.WAITING:
            if event == message.MessageTypes.FOLLOW:
                self.handle_follow(msg)
            elif event == message.MessageTypes.MERGE:
                self.handle_merge(msg)
            elif event == message.MessageTypes.FOLLOW_MERGE:
                self.handle_follow_merge(msg)
            elif event == message.MessageTypes.SET_AVAILABLE:
                self.enter(StateTypes.AVAILABLE)
            elif event == message.MessageTypes.CHALLENGE_INIT:
                self.handle_challenge_init(msg)
            elif event == message.MessageTypes.CHALLENGE_ACK:
                self.handle_challenge_ack(msg)
            elif event == message.MessageTypes.SIZE_QUERY:
                self.handle_size_query(msg)
            elif event == message.MessageTypes.SIZE_REPLY:
                self.handle_size_reply(msg)

        if event == message.MessageTypes.STOP:
            server_message = message.Message(message.MessageTypes.FIN).from_fls(self.context).to_server()
            self.sock.send_to_server(server_message)
