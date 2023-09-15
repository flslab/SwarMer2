import threading
import time
from message import MessageTypes


class HandlerThread(threading.Thread):
    def __init__(self, event_queue, state_machine, context):
        super(HandlerThread, self).__init__()
        self.event_queue = event_queue
        self.state_machine = state_machine
        self.context = context
        self.last_thaw = 0

    def run(self):
        self.state_machine.start()
        while True:
            item = self.event_queue.get()
            if item.stale:
                continue

            event = item.event
            # if event.type == MessageTypes.THAW_SWARM:
            #     t = time.time()
            #
            #     if t - self.last_thaw > 4:
            #         self.flush_all()
            #     else:
            #         continue
            #     self.last_thaw = t
            self.state_machine.drive(event)
            if event.type == MessageTypes.STOP:
                # print(f"handler_stopped_{self.context.fid}")
                break

            self.flush_queue()

    def flush_queue(self):
        with self.event_queue.mutex:
            for item in self.event_queue.queue:
                t = item.event.type
                if t == MessageTypes.SIZE_REPLY or t == MessageTypes.THAW_SWARM or t == MessageTypes.STOP\
                        or t == MessageTypes.LEASE_RENEW or t == MessageTypes.LEASE_CANCEL:
                    item.stale = False
                elif t == MessageTypes.RENEW_LEASE_INTERNAL \
                        or t == MessageTypes.SET_AVAILABLE_INTERNAL \
                        or t == MessageTypes.FAIL_INTERNAL \
                        or t == MessageTypes.THAW_SWARM_INTERNAL:
                    item.stale = False
                elif t == MessageTypes.CHALLENGE_FIN or t == MessageTypes.CHALLENGE_INIT\
                        or t == MessageTypes.CHALLENGE_ACK or t == MessageTypes.CHALLENGE_ACCEPT:
                    if item.event.swarm_id != self.context.swarm_id:
                        item.stale = False
                    else:
                        item.stale = True
                else:
                    item.stale = True

    def flush_all(self):
        with self.event_queue.mutex:
            for item in self.event_queue.queue:
                item.stale = True
