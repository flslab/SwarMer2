class WorkerContext:
    def __init__(self, count, fid, gtl, el):
        self.count = count
        self.fid = fid
        self.gtl = gtl
        self.el = el
        self.swarm_id = self.fid
        self.neighbors_id = []
        self.radio_range = 100

    def fly(self, vector):
        pass
