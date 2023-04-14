import time
import numpy as np


class MetricTypes:
    RECEIVED_MASSAGES = 0
    SENT_MESSAGES = 1
    LOCATION = 2
    SWARM_ID = 3
    LEASES = 4
    WAITS = 5
    ANCHOR = 6
    LOCALIZE = 7


class Metrics:
    def __init__(self, history):
        self.rounds_timestamp = []
        self.history = history

    def set_round_times(self, times):
        self.rounds_timestamp = times

    def get_total_distance(self):
        way_points = self.get_location_history()
        total_dist = 0
        for i in range(len(way_points) - 1):
            d = np.linalg.norm(way_points[i+1].value - way_points[i].value)
            total_dist += d

        return total_dist

    def get_total_bytes_sent(self):
        return sum([s.meta["length"] for s in self.get_sent_messages()])

    def get_total_bytes_received(self):
        return sum([s.meta["length"] for s in self.get_received_messages()])

    def get_bytes_sent_histogram(self):
        hist = dict()

        for msg_hist in self.get_sent_messages():
            msg_type = msg_hist.value
            msg_length = msg_hist.meta["length"]

            if msg_type in hist:
                hist[msg_type] += msg_length
            else:
                hist[msg_type] = msg_length

        return hist

    def get_bytes_received_histogram(self):
        hist = dict()

        for msg_hist in self.get_received_messages():
            msg_type = msg_hist.value
            msg_length = msg_hist.meta["length"]

            if msg_type in hist:
                hist[msg_type] += msg_length
            else:
                hist[msg_type] = msg_length

        return hist

    def get_location_history(self):
        return self.history[MetricTypes.LOCATION]

    def get_received_messages(self):
        return self.history[MetricTypes.RECEIVED_MASSAGES]

    def get_sent_messages(self):
        return self.history[MetricTypes.SENT_MESSAGES]

    def get_expired_leases(self):
        return self.history[MetricTypes.LEASES]

    def get_waits(self):
        return self.history[MetricTypes.WAITS]

    def get_final_report(self):
        waits = [d.value for d in self.get_waits()]
        report = {
            "total_distance": self.get_total_distance(),
            "num_moved": len(waits),
            "min_wait": min(waits),
            "avg_wait": sum(waits),
            "max_wait": max(waits),
            "total_bytes_sent": sum([s.meta["length"] for s in self.get_sent_messages()]),
            "total_bytes_received": sum([r.meta["length"] for r in self.get_received_messages()]),
            "num_expired_leases": len(self.get_expired_leases()),
            "num_anchor": len(self.history[MetricTypes.ANCHOR]),
            "num_localize": len(self.history[MetricTypes.LOCALIZE])
        }

        return report
