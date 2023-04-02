import multiprocessing
import queue

import state
from .network import NetworkThread
from .handler import HandlerThread
from .socket import WorkerSocket
from .context import WorkerContext

broadcast_address = ("<broadcast>", 5000)


class WorkerProcess(multiprocessing.Process):
    def __init__(self, count, process_id, gtl, el, shared_el, barrier):
        super(WorkerProcess, self).__init__()
        self.context = WorkerContext(count, process_id, gtl, el, shared_el)
        self.sock = WorkerSocket()
        self.barrier = barrier

    def run(self):
        event_queue = queue.PriorityQueue()
        state_machine = state.StateMachine(self.context, self.sock, self.barrier)
        network_thread = NetworkThread(event_queue, self.context, self.sock)
        handler_thread = HandlerThread(event_queue, state_machine)
        network_thread.start()
        handler_thread.start()

        network_thread.join()
        handler_thread.join()
