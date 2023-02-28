import time


class WorkerContext:
    def __init__(self, count, fid, gtl, el, neighbors):
        self.count = count
        self.fid = fid
        self.gtl = gtl
        self.el = el
        self.swarm_id = self.fid
        self.neighbors = dict(zip(neighbors, neighbors))
        self.radio_range = 100
        self.size = 1
        self.anchor = None
        self.query_id = None
        self.history_el = {time.time(): self.el}
        self.history_swarm_id = {time.time(): self.swarm_id}

    def set_swarm_id(self, swarm_id):
        self.swarm_id = swarm_id
        self.history_swarm_id[time.time()] = self.swarm_id

    def set_el(self, el):
        self.el = el
        self.history_el[time.time()] = self.el

    def set_query_id(self, query_id):
        self.query_id = query_id

    def set_anchor(self, anchor):
        self.anchor = anchor

    def move(self, vector):
        self.set_el(self.el + vector)

    def update_neighbor(self, ctx):
        if ctx.fid in self.neighbors:
            self.neighbors[ctx.fid] = ctx.swarm_id
