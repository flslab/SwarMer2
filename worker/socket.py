import socket
import pickle
import select
from constants import Constants


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
        return msg, len(data)

    def broadcast(self, msg, retry=2):
        data = pickle.dumps(msg)
        try:
            self.sock.sendto(data, Constants.BROADCAST_ADDRESS)
        except OSError:
            if retry:
                self.broadcast(msg, retry - 1)
        return len(data)

    def send_to_server(self, msg):
        self.sock.sendto(pickle.dumps(msg), Constants.SERVER_ADDRESS)

    def is_ready(self):
        ready = select.select([self.sock], [], [], 1)
        return ready[0]
