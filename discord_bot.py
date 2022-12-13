from config import *
from logging_config import DISCORD_LOGGER
from discord.client import Client
from discord import Intents
from modules import Thread

class DiscordClient(Client):
    def __init__(self, *args, **kwargs):
        intents = Intents.all()
        super().__init__(*args, **kwargs, intents=intents)
        self.first_connect = True
    
    async def on_ready(self):
        DISCORD_LOGGER.info(f"Discord Bot {self.user} Ready!")
    
    def run(self, *args, **kwargs) -> None:
        return super().run(DISCORD_TOKEN, *args, **kwargs)

def run() -> Thread:
    client = DiscordClient()
    thread = Thread(target=client.run, name="Discord")
    thread.start()
    return thread

if __name__ == "__main__":
    client = DiscordClient()
    client.run()