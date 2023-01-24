from .fix_module import bridge_command, response

from discord import Bot, Cog
from discord.ext.bridge import BridgeContext

class HelloWorldCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @bridge_command(name="helloworld")
    async def hello_world(self, ctx: BridgeContext):
        await response(ctx=ctx, content="Hello World")

def setup(bot: Bot):
    bot.add_cog(HelloWorldCog(bot))
