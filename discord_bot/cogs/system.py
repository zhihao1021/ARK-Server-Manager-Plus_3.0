from .config import ADMIN_PERMISSION
from .fix_module import bridge_group, response

from asyncio import get_event_loop, sleep as asleep
from io import BytesIO
from os import _exit, system
from subprocess import run, PIPE
from typing import Optional

from discord import Cog, Message, File
from discord.ext.bridge import Bot, BridgeContext

class SystemCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
    
    @bridge_group(default_member_permissions=ADMIN_PERMISSION)
    async def system(self, ctx: BridgeContext):
        ...
    
    @system.command(name="stop-bot")
    async def stop_bot(self, ctx: BridgeContext):
        await response(ctx=ctx, content="Stop in 5 Second...")
        await asleep(5)
        _exit(0)

    @system.command(name="restart-bot")
    async def restart_bot(self, ctx: BridgeContext, update: Optional[bool]=False):
        await response(ctx=ctx, content="Restart in 5 Second...")
        if update:
            system("start cmd /c \"git pull && start.cmd\"")
        else:
            system("start start.cmd")
        await asleep(5)
        _exit(0)
    
    @system.command(name="update-bot")
    async def update_bot(self, ctx: BridgeContext):
        loop = get_event_loop()
        mes = await response(ctx=ctx, content="Querying...")
        res = await loop.run_in_executor(None, lambda: run("git pull", stdout=PIPE, stderr=PIPE))
        files = []
        if res.stdout != None and res.stdout != b"":
            __pre = "STDOUT - Update:\n"
            files.append(File(BytesIO(__pre.encode() + res.stdout), filename="stdout.log"))
        if res.stderr != None and res.stderr != b"":
            __pre = "STDERR - Update:\n"
            files.append(File(BytesIO(__pre.encode() + res.stderr), filename="stderr.log"))
        
        if type(mes) == Message:
            await mes.edit(content="Result:", files=files)
        else:
            await mes.edit_original_response(content="Result:", files=files)
    
    @system.command(name="system-command")
    async def system_command(self, ctx: BridgeContext, command: str):
        loop = get_event_loop()
        mes = await response(ctx=ctx, content="Querying...")
        res = await loop.run_in_executor(None, lambda: run(command, stdout=PIPE, stderr=PIPE))
        files = []
        if res.stdout != None and res.stdout != b"":
            __pre = "STDOUT - " + command + ":\n"
            files.append(File(BytesIO(__pre.encode() + res.stdout), filename="stdout.log"))
        if res.stderr != None and res.stderr != b"":
            __pre = "STDERR - " + command + ":\n"
            files.append(File(BytesIO(__pre.encode() + res.stderr), filename="stderr.log"))
        
        if type(mes) == Message:
            await mes.edit(content="Result:", files=files)
        else:
            await mes.edit_original_response(content="Result:", files=files)

def setup(bot: Bot):
    bot.add_cog(SystemCog(bot))
