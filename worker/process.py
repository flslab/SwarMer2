import message
import time
import multiprocessing
from .socket import WorkerSocket
from utils.log import log


broadcast_address = ("<broadcast>", 5000)


class WorkerProcess(multiprocessing.Process):
    def __init__(self, process_id):
        super(WorkerProcess, self).__init__()
        self.id = process_id
        self.sock = WorkerSocket()

    def run(self):
        self.sock.init()

        while True:
            # Check if message is available
            if self.sock.is_ready():
                msg = self.receive_message()
                if msg.type == message.MessageTypes.STOP:
                    break

            # Broadcast message
            msg = message.Message(message.MessageTypes.DUMMY, f"Hello from worker {self.id}")
            self.broadcast_message(msg)
            time.sleep(1)

        self.sock.close()

    def receive_message(self):
        msg = self.sock.receive()
        log(f"Process {self.id}: Received message - {msg}")
        return msg

    def broadcast_message(self, msg):
        self.sock.broadcast(msg)
