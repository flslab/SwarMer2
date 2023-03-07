import threading
import numpy as np

import message


class NetworkThread(threading.Thread):
    def __init__(self, event_queue, context, sock):
        super(NetworkThread, self).__init__()
        self.event_queue = event_queue
        self.context = context
        self.sock = sock

    def run(self):
        while True:
            # if self.sock.is_ready():
            msg = self.sock.receive()
            if self.is_message_valid(msg):
                self.event_queue.put(msg)
                if msg.type == message.MessageTypes.STOP:
                    break

    def is_message_valid(self, msg):
        if msg.fid == self.context.fid:
            return False
        if msg.dest_fid != self.context.fid and msg.dest_fid != '*':
            return False
        if msg.dest_swarm_id != self.context.swarm_id and msg.dest_swarm_id != '*':
            return False
        if msg.el is not None:
            dist = np.linalg.norm(msg.el - self.context.el)
            if dist > msg.range:
                return False
        return True
