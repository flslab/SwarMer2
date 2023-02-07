class Message:
    def __init__(self, message_type, payload):
        self.type = message_type
        self.payload = payload

    def __repr__(self):
        return f"Message(type={self.type.name}, payload={self.payload})"
