import time
import heapq
from functools import total_ordering


class History:
    def __init__(self, size):
        self.lists = dict()
        for i in range(size):
            self.lists[i] = []

    def log(self, category, value):
        entry = HistoryEntry(category, value)
        self.lists[category].append(entry)

    def merge_lists(self):
        lists = list(self.lists.values())
        heap = []
        for i, lst in enumerate(lists):
            if lst:
                heap.append((lst[0], i, 0))
        heapq.heapify(heap)

        merged = []
        while heap:
            val, lst_idx, elem_idx = heapq.heappop(heap)
            merged.append(lists[lst_idx][elem_idx])
            if elem_idx + 1 < len(lists[lst_idx]):
                next_elem = lists[lst_idx][elem_idx + 1]
                heapq.heappush(heap, (next_elem, lst_idx, elem_idx + 1))
        return merged


@total_ordering
class HistoryEntry:
    def __init__(self, category, value):
        self.t = time.time()
        self.category = category
        self.value = value

    def __eq__(self, other):
        return self.t == other.t

    def __lt__(self, other):
        return self.t < other.t

    def __repr__(self):
        return f"{self.t} {self.category} {self.value}"
