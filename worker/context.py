class WorkerContext:
    def __init__(self, fid, gtl, el):
        self.fid = fid
        self.gtl = gtl
        self.el = el
        self.swarm_id = self.fid
        self.neighbors_id = []
        self.radio_range = 10

    def fly(self, vector):
        pass
