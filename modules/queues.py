from queue import Queue
from time import time
from typing import Literal, Optional

class C_Queue(Queue):
    def clear(self, timeout: int=0):
        s_time = time()
        while not self.empty():
            self.get()
            if time() - s_time > timeout and timeout:
                return

class DiscordMessage:
    CHANNEL_ID: int
    CONTENT: str
    def __init__(self,
        channel_id: int,
        content: str,
    ) -> None:
        self.CHANNEL_ID = channel_id
        self.CONTENT = content

class ARKCommand:
    COMMAND_TYPE: Literal["command", "aio-command"]
    SERVER_ID: str
    CONTENT: str
    RETURN_QUEUE: Literal["discord", "web"]
    ARGS: Optional[tuple]
    KWARGS: Optional[dict]
    def __init__(self,
        _type: Literal["command", "aio-command"],
        server_id: str,
        content: str,
        return_queue: Literal["discord", "web"],
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ) -> None:
        self.COMMAND_TYPE = _type
        self.SERVER_ID = server_id
        self.CONTENT = content
        self.RETURN_QUEUE = return_queue
        self.ARGS = args
        self.KWARGS = kwargs

class WebCommand:
    COMMAND_TYPE: Literal["broadcast", "r_command"]
    CONTENT: str
    ARGS: Optional[tuple]
    KWARGS: Optional[dict]
    def __init__(self,
        _type: Literal["broadcast", "r_command"],
        content: str,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ) -> None:
        self.COMMAND_TYPE = _type
        self.CONTENT = content
        self.ARGS = args
        self.KWARGS = kwargs

DISCORD_COMMAND = C_Queue()
ARK_COMMAND = C_Queue()
WEB_COMMAND = C_Queue()
