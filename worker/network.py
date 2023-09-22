import random
import time
from dataclasses import dataclass, field
from socket import socket
from typing import Any
import threading
import numpy as np
from config import Config
import message
from message import MessageTypes
from state import StateTypes


general_messages = {
    MessageTypes.STOP,
    MessageTypes.THAW_SWARM,
}

available_state_messages = {
    MessageTypes.CHALLENGE_INIT,
    MessageTypes.CHALLENGE_ACCEPT,
    MessageTypes.CHALLENGE_ACK,
    MessageTypes.SET_WAITING,
}

anchor_state_messages = {
    MessageTypes.LEASE_RENEW,
    MessageTypes.MERGE,
    MessageTypes.CHALLENGE_FIN,
    MessageTypes.LEASE_CANCEL,
    MessageTypes.CHALLENGE_ACK,
}

localizing_state_messages = {
    MessageTypes.CHALLENGE_ACK,
}

waiting_state_messages = {
    MessageTypes.FOLLOW,
    MessageTypes.MERGE,
    MessageTypes.FOLLOW_MERGE,
    MessageTypes.SET_AVAILABLE,
    MessageTypes.CHALLENGE_ACK,
}

valid_state_messages = {
    StateTypes.AVAILABLE: available_state_messages,
    StateTypes.WAITING: waiting_state_messages,
    StateTypes.BUSY_ANCHOR: anchor_state_messages,
    StateTypes.BUSY_LOCALIZING: localizing_state_messages,
    StateTypes.DEPLOYING: dict(),
}


class NetworkThread(threading.Thread):
    def __init__(self, event_queue, state_machine, context, sock):
        super(NetworkThread, self).__init__()
        self.event_queue = event_queue
        self.state_machine = state_machine
        self.context = context
        self.sock = sock
        self.latest_message_id = dict()
        self.last_lease_renew = 0
        self.last_challenge = 0
        self.start_time = 0
        self.last_fail_check = 0

    def run(self):
        self.start_time = time.time()
        self.last_fail_check = self.start_time + 1
        while True:
            t = time.time()
            if t - self.last_lease_renew > 0.5 * Config.CHALLENGE_LEASE_DURATION:
                if self.state_machine.state == StateTypes.BUSY_LOCALIZING:
                    # msg = Message(MessageTypes.RENEW_LEASE_INTERNAL).to_fls(self.context)
                    # item = PrioritizedItem(1, time.time(), msg, False)
                    # self.event_queue.put(item)
                    self.state_machine.renew_lease()
                    self.last_lease_renew = t
            if t - self.last_challenge > Config.STATE_TIMEOUT:
                if self.state_machine.state != StateTypes.BUSY_ANCHOR \
                        and self.state_machine.state != StateTypes.BUSY_LOCALIZING \
                        and self.state_machine.state != StateTypes.DEPLOYING:
                    # msg = Message(MessageTypes.SET_AVAILABLE_INTERNAL).to_fls(self.context)
                    # item = PrioritizedItem(1, time.time(), msg, False)
                    # self.event_queue.put(item)
                    self.state_machine.reenter_available_state()
                    self.last_challenge = t
            if t - self.start_time > Config.DURATION + 15:
                break
            if Config.FAILURE_TIMEOUT and t - self.last_fail_check > Config.FAILURE_TIMEOUT:
                self.state_machine.set_fail()
                self.last_fail_check = t
            if random.random() < 0.001:
                time.sleep(0.005)
            # if self.sock.is_ready():
            try:
                msg, length = self.sock.receive()
            except BlockingIOError:
                continue
            except Exception:
                continue
            # self.context.log_received_message(msg.type, length)
            if self.is_message_valid(msg):
                # if msg.type == message.MessageTypes.THAW_SWARM:
                #     print(self.context.fid, msg)
                self.context.log_received_message(msg.type, length)
                self.latest_message_id[msg.fid] = msg.id
                self.handle_immediately(msg)
                if msg is not None and msg.type == message.MessageTypes.STOP:
                    # print(f"network_stopped_{self.context.fid}")
                    break

    def handle_immediately(self, msg):
        if self.state_machine.state == StateTypes.BUSY_ANCHOR:
            if msg.type == MessageTypes.CHALLENGE_ACK:
                self.state_machine.handle_challenge_ack_anchor(msg)
                return
        elif self.state_machine.state == StateTypes.WAITING:
            if msg.type == MessageTypes.CHALLENGE_ACK:
                self.state_machine.handle_challenge_ack_anchor(msg)
                return
        elif self.state_machine.state == StateTypes.BUSY_LOCALIZING:
            if msg.type == MessageTypes.CHALLENGE_ACK:
                self.state_machine.handle_challenge_ack_anchor(msg)
                return

        self.event_queue.put(NetworkThread.prioritize_message(msg))

    def is_message_valid(self, msg):
        if msg is None:
            self.context.log_dropped_messages()
            return False
        if msg.type == message.MessageTypes.STOP:
            return True
        if Config.DROP_PROB_RECEIVER:
            if np.random.random() <= Config.DROP_PROB_RECEIVER:
                self.context.log_dropped_messages()
                return False
        if msg.fid == self.context.fid:
            return False
        if msg.dest_fid != self.context.fid and msg.dest_fid != '*':
            return False
        if msg.dest_swarm_id != self.context.swarm_id and msg.dest_swarm_id != '*':
            return False
        if msg.fid in self.latest_message_id and msg.id < self.latest_message_id[msg.fid]:
            return False
        if msg.type == message.MessageTypes.CHALLENGE_INIT or msg.type == message.MessageTypes.GOSSIP:
            dist = np.linalg.norm(msg.el - self.context.el)
            if dist > msg.range:
                return False
        if self.state_machine in valid_state_messages:
            if msg.type not in valid_state_messages[self.state_machine.state] or msg.type not in general_messages:
                return False
        return True

    @staticmethod
    def prioritize_message(msg):
        t = time.time()
        if msg.type == message.MessageTypes.STOP or msg.type == message.MessageTypes.THAW_SWARM:
            return PrioritizedItem(0, t, msg, False)
        if msg.type == message.MessageTypes.SIZE_QUERY or msg.type == message.MessageTypes.SIZE_REPLY:
            return PrioritizedItem(2, t, msg, False)
        if msg.type == message.MessageTypes.SET_WAITING or msg.type == message.MessageTypes.FOLLOW_MERGE\
                or msg.type == message.MessageTypes.FOLLOW or msg.type == message.MessageTypes.MERGE\
                or msg.type == message.MessageTypes.CHALLENGE_FIN:
            return PrioritizedItem(1, t, msg, False)
        return PrioritizedItem(3, t, msg, False)


@dataclass(order=True)
class PrioritizedItem:
    priority: int
    time: float
    event: Any = field(compare=False)
    stale: bool = field(compare=False)
