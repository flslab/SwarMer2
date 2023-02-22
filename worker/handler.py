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
            event = self.event_queue.get()
            self.state_machine.drive(event)
            if event.type == message.MessageTypes.STOP:
                break
