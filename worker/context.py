class WorkerContext:
    def __init__(self, count, fid, gtl, el):
        self.count = count
        self.fid = fid
        self.gtl = gtl
        self.el = el
        self.swarm_id = self.fid
        self.neighbors_id = []
        self.radio_range = 100
        self.size = 1
        self.anchor = None
        self.query_id = None

    def fly(self, vector):
        pass
