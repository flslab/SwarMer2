import socket
import pickle
import select


BROADCAST_ADDRESS = ("<broadcast>", 5000)
PORT = 5000


class WorkerSocket:
    def __init__(self):
        self.sock = None
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", PORT))
        self.sock = sock

    def close(self):
        self.sock.close()

    def receive(self):
        data, _ = self.sock.recvfrom(1024)
        msg = pickle.loads(data)
        return msg

    def broadcast(self, msg, retry=2):
        try:
            self.sock.sendto(pickle.dumps(msg), BROADCAST_ADDRESS)
        except OSError:
            if retry:
                self.broadcast(msg, retry-1)

    def is_ready(self):
        ready = select.select([self.sock], [], [], 1)
        return ready[0]
