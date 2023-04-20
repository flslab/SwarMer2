import multiprocessing
import queue

import state
from .network import NetworkThread
from .handler import HandlerThread
from .socket import WorkerSocket
from .context import WorkerContext
from .history import History
from .metrics import Metrics

broadcast_address = ("<broadcast>", 5000)


class WorkerProcess(multiprocessing.Process):
    def __init__(self, count, process_id, gtl, el, shared_el, results_directory):
        super(WorkerProcess, self).__init__()
        self.history = History(8)
        self.metrics = Metrics(self.history, results_directory)
        self.context = WorkerContext(count, process_id, gtl, el, shared_el, self.history)
        self.sock = WorkerSocket()
        self.state_machine = state.StateMachine(self.context, self.sock, self.metrics)

    def run(self):
        event_queue = queue.PriorityQueue()

        network_thread = NetworkThread(event_queue, self.context, self.sock)
        handler_thread = HandlerThread(event_queue, self.state_machine)
        network_thread.start()
        handler_thread.start()

        network_thread.join()
        handler_thread.join()
