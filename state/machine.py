import message
from .types import StateTypes


class StateMachine:
    def __init__(self, context, sock):
        self.state = StateTypes.AVAILABLE
        self.context = context
        self.sock = sock
        self.size = 1

    def start(self):
        self.enter(StateTypes.AVAILABLE)

    def handle_size_query(self, msg):
        resp = message.Message(message.MessageTypes.SIZE_REPLY).from_fls(self.context).to_fls(msg)
        self.sock.broadcast(resp)

    def handle_size_reply(self, msg):
        self.size += 1
        print(self.size)

    def enter_available_state(self):
        if self.context.fid == 1:
            self.size = 1
            resp = message.Message(message.MessageTypes.SIZE_QUERY).from_fls(self.context).to_all()
            self.sock.broadcast(resp)

    def enter_busy_localizing_state(self):
        pass

    def enter_busy_anchor_state(self):
        pass

    def enter_waiting_state(self):
        pass

    def enter(self, state):
        self.state = state

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
                pass
            elif event == message.MessageTypes.CHALLENGE_ACCEPT:
                pass
            elif event == message.MessageTypes.CHALLENGE_ACK:
                pass
            elif event == message.MessageTypes.SIZE_QUERY:
                self.handle_size_query(msg)
            elif event == message.MessageTypes.SIZE_REPLY:
                self.handle_size_reply(msg)

        elif self.state == StateTypes.BUSY_LOCALIZING:
            if event == message.MessageTypes.LEASE_GRANT:
                pass
            elif event == message.MessageTypes.SIZE_QUERY:
                pass

        elif self.state == StateTypes.BUSY_ANCHOR:
            if event == message.MessageTypes.LEASE_RENEW:
                pass
            elif event == message.MessageTypes.MERGE:
                pass
            elif event == message.MessageTypes.CHALLENGE_FIN:
                pass
            elif event == message.MessageTypes.SIZE_QUERY:
                pass

        elif self.state == StateTypes.WAITING:
            if event == message.MessageTypes.FOLLOW:
                pass
            elif event == message.MessageTypes.MERGE:
                pass
            elif event == message.MessageTypes.FOLLOW_MERGE:
                pass
            elif event == message.MessageTypes.SET_AVAILABLE:
                pass
            elif event == message.MessageTypes.CHALLENGE_INIT:
                pass
            elif event == message.MessageTypes.CHALLENGE_ACK:
                pass
            elif event == message.MessageTypes.SIZE_QUERY:
                pass
            elif event == message.MessageTypes.SIZE_REPLY:
                pass
