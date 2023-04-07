import socket
import pickle
import select
import numpy as np
from constants import Constants
from config import Config


class WorkerSocket:
    def __init__(self):
        self.sock = None
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(Constants.WORKER_ADDRESS)
        self.sock = sock

    def close(self):
        self.sock.close()

    def receive(self):
        data, _ = self.sock.recvfrom(1024)
        msg = pickle.loads(data)

        if Config.DROP_PROB_RECEIVER:
            if np.random.random() <= Config.DROP_PROB_SENDER:
                return None, 0

        return msg, len(data)

    def broadcast(self, msg, retry=2):
        if Config.DROP_PROB_SENDER:
            if np.random.random() <= Config.DROP_PROB_SENDER:
                return 0

        data = pickle.dumps(msg)
        try:
            self.sock.sendto(data, Constants.BROADCAST_ADDRESS)
        except OSError:
            if retry:
                self.broadcast(msg, retry - 1)
        return len(data)

    def send_to_server(self, msg):
        data = pickle.dumps(msg)
        self.sock.sendto(data, Constants.SERVER_ADDRESS)
        return len(data)

    def is_ready(self):
        ready = select.select([self.sock], [], [], 1)
        return ready[0]
