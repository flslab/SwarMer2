class Message:
    def __init__(self, message_type, fid=0, swarm_id=0, dest_fid="*", dest_swarm_id="*", location=None, params=None):
        self.type = message_type
        self.fid = fid
        self.swarm_id = swarm_id
        self.dest_fid = dest_fid
        self.dest_swarm_id = dest_swarm_id
        self.location = location
        self.params = params

    def from_fls(self, ctx):
        self.fid = ctx.fid
        self.swarm_id = ctx.swarm_id
        self.location = ctx.el
        return self

    def from_server(self):
        self.fid = 0
        self.swarm_id = 0
        return self

    def to_all(self):
        self.dest_fid = "*"
        self.dest_swarm_id = "*"
        return self

    def to_swarm(self, ctx):
        self.dest_fid = "*"
        self.dest_swarm_id = ctx.swarm_id
        return self

    def to_fls(self, ctx):
        self.dest_fid = ctx.fid
        self.dest_swarm_id = ctx.swarm_id
        return self

    def __repr__(self):
        return f"Message(type={self.type.name}," \
               f"from={self.fid}:{self.swarm_id}," \
               f"to={self.dest_fid}:{self.dest_swarm_id})"
