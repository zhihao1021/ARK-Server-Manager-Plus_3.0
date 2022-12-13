from queue import Queue
from time import time
from typing import Optional

class C_Queue(Queue):
    def clear(self, timeout: int=0):
        s_time = time()
        while not self.empty():
            self.get()
            if time() - s_time > timeout and timeout:
                return

DISCORD_MESSAGE_IN = C_Queue()
