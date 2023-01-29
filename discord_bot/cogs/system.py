from .config import ADMIN_PERMISSION
from .fix_module import bridge_group, response

from asyncio import sleep as asleep
from os import _exit, system

from discord import Cog
from discord.ext.bridge import Bot, BridgeContext

class SystemCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
    
    @bridge_group(default_member_permissions=ADMIN_PERMISSION)
    async def system(self, ctx: BridgeContext):
        ...
    
    @system.command(name="stop-bot")
    async def stop(self, ctx: BridgeContext):
        await response(ctx=ctx, content="Stop in 5 Second...")
        await asleep(5)
        _exit(0)

    @system.command(name="restart-bot")
    async def restart_bot(self, ctx: BridgeContext):
        await response(ctx=ctx, content="Restart in 5 Second...")
        system("start start.cmd")
        await asleep(5)
        _exit(0)

def setup(bot: Bot):
    bot.add_cog(SystemCog(bot))
