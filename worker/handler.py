import threading
import message


class HandlerThread(threading.Thread):
    def __init__(self, event_queue, state_machine):
        super(HandlerThread, self).__init__()
        self.event_queue = event_queue
        self.state_machine = state_machine

    def run(self):
        self.state_machine.start()
        while True:
            item = self.event_queue.get()
            if item.stale:
                continue

            event = item.event
            self.state_machine.drive(event)
            self.flush_queue()

            if event.type == message.MessageTypes.STOP:
                break

    def flush_queue(self):
        with self.event_queue.mutex:
            for item in self.event_queue.queue:
                if item.event.type == message.MessageTypes.SIZE_REPLY:
                    item.stale = False
                else:
                    item.stale = True
