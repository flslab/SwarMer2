class Message:
    def __init__(self, message_type, fid, swarm_id, dest_fid="*", dest_swarm_id="*", location=None, params=None):
        self.type = message_type
        self.fid = fid
        self.swarm_id = swarm_id
        self.dest_fid = dest_fid
        self.dest_swarm_id = dest_swarm_id
        self.location = location
        self.params = params

    def __repr__(self):
        return f"Message(type={self.type.name}," \
               f"from={self.fid}:{self.swarm_id}," \
               f"to={self.dest_fid}:{self.dest_swarm_id})"
