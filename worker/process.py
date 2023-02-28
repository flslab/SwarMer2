import multiprocessing
import queue

import state
from .network import NetworkThread
from .handler import HandlerThread
from .socket import WorkerSocket
from .context import WorkerContext

broadcast_address = ("<broadcast>", 5000)


class WorkerProcess(multiprocessing.Process):
    def __init__(self, count, process_id, gtl, el, knn):
        super(WorkerProcess, self).__init__()
        self.context = WorkerContext(count, process_id, gtl, el, knn)
        self.sock = WorkerSocket()

    def run(self):
        event_queue = queue.Queue()
        state_machine = state.StateMachine(self.context, self.sock)
        network_thread = NetworkThread(event_queue, self.context, self.sock)
        handler_thread = HandlerThread(event_queue, state_machine)
        network_thread.start()
        handler_thread.start()

        network_thread.join()
        handler_thread.join()
