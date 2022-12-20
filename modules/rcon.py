from rcon.source import Client
from configs import *

class RCON_Client:
    def __init__(self, unique_key: str) -> None:
        self.address = SERVERS[unique_key].RCON_ADDRESS
        self.port = SERVERS[unique_key].RCON_PORT
        self.password = SERVERS[unique_key].RCON_PASSWORD
        self.timeout = SERVERS[unique_key].RCON_TIMEOUT
