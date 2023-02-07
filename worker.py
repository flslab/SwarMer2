import message
import socket
import pickle
import time
import select
import multiprocessing
from utils.log import log


broadcast_address = ("<broadcast>", 5000)


class WorkerProcess(multiprocessing.Process):
    def __init__(self, process_id):
        super(WorkerProcess, self).__init__()
        self.id = process_id
        self.sock = None

    def run(self):
        self.create_socket()

        while True:
            # Check if message is available
            ready = select.select([self.sock], [], [], 1)
            if ready[0]:
                msg = self.receive_message()
                if msg.type == message.MessageTypes.STOP:
                    break

            # Broadcast message
            msg = message.Message(message.MessageTypes.DUMMY, f"Hello from worker {self.id}")
            self.broadcast_message(msg)
            time.sleep(1)

        self.close_socket()

    def create_socket(self):
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", 5000))
        self.sock = sock

    def close_socket(self):
        self.sock.close()

    def receive_message(self):
        # Receive message
        data, _ = self.sock.recvfrom(1024)
        msg = pickle.loads(data)
        log(f"Process {self.id}: Received message - {msg}")
        return msg

    def broadcast_message(self, message, retry=2):
        try:
            self.sock.sendto(pickle.dumps(message), broadcast_address)
        except OSError:
            if retry:
                self.broadcast_message(message, retry-1)
