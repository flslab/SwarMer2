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
    DROPPED_MESSAGES = 8
    FAILURES = 9


def get_messages_histogram(msgs, label):
    hist = dict()

    for msg_hist in msgs:
        msg_type = msg_hist.value
        msg_length = msg_hist.meta["length"]
        key_bytes = f'bytes_{label}_{msg_type.name}'
        key_number = f'num_{label}_{msg_type.name}'
        key_bytes_cat = f'bytes_{label}_cat_{msg_type.get_cat()}'
        key_num_cat = f'num_{label}_cat_{msg_type.get_cat()}'

        if key_number in hist:
            # hist[key_bytes] += msg_length
            hist[key_number] += 1
        else:
            # hist[key_bytes] = msg_length
            hist[key_number] = 1

        if key_num_cat in hist:
            # hist[key_bytes_cat] += msg_length
            hist[key_num_cat] += 1
        else:
            # hist[key_bytes_cat] = msg_length
            hist[key_num_cat] = 1

    return hist


class Metrics:
    def __init__(self, history, results_directory):
        self.results_directory = results_directory
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

    def get_sent_messages_histogram(self):
        return get_messages_histogram(self.get_sent_messages(), 'sent')

    def get_received_messages_histogram(self):
        return get_messages_histogram(self.get_received_messages(), 'received')

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

    def get_dropped_messages(self):
        return self.history[MetricTypes.DROPPED_MESSAGES]

    def get_failures(self):
        return self.history[MetricTypes.FAILURES]

    def get_final_report(self):
        waits = [d.value for d in self.get_waits()]
        report = {
            "total_distance": self.get_total_distance(),
            "num_moved": len(waits),
            "min_wait(s)": min(waits),
            "max_wait(s)": max(waits),
            "total_wait(s)": sum(waits),
            "num_expired_leases": len(self.get_expired_leases()),
            "num_anchor": len(self.history[MetricTypes.ANCHOR]),
            "num_localize": len(self.history[MetricTypes.LOCALIZE]),
            "bytes_sent": sum([s.meta["length"] for s in self.get_sent_messages()]),
            "bytes_received": sum([r.meta["length"] for r in self.get_received_messages()]),
            "num_messages_sent": len(self.get_sent_messages()),
            "num_messages_received": len(self.get_received_messages()),
            "num_dropped_messages": len(self.get_dropped_messages()),
            "num_failures": len(self.get_failures())
        }

        report.update(self.get_sent_messages_histogram())
        report.update(self.get_received_messages_histogram())

        return report
