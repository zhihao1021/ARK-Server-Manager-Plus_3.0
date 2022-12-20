from configs import *

class ARKServer:
    def __init__(self, unique_id: str) -> None:
        self.unqiue_id = unique_id
        self.config = SERVERS[unique_id]

