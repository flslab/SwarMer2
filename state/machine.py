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
        resp = message.Message(
            message.MessageTypes.SIZE_REPLY,
            self.context.fid, self.context.swarm_id, msg.fid, msg.swarm_id)
        self.sock.broadcast(resp)

    def handle_size_reply(self, msg):
        self.size += 1
        print(self.size)

    def enter(self, state):
        self.state = state

        if self.state == StateTypes.AVAILABLE:
            if self.context.fid == 1:
                resp = message.Message(
                    message.MessageTypes.SIZE_QUERY,
                    self.context.fid, self.context.swarm_id, "*", "*")
                self.sock.broadcast(resp)
        elif self.state == StateTypes.BUSY_LOCALIZING:
            pass
        elif self.state == StateTypes.BUSY_ANCHOR:
            pass
        elif self.state == StateTypes.WAITING:
            pass

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
