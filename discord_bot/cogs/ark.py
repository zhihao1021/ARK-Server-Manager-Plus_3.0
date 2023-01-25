from .fix_module import bridge_group, response

from ark_module import ARK_SERVERS, ARKServer
from configs import DISCORD_CONFIG, STATUS_MESSAGES

from asyncio import get_event_loop
from typing import Optional

from discord import Cog,  Option, OptionChoice, Message
from discord.ext.bridge import Bot, BridgeContext

class ArkCog(Cog):
    operation_options = [
        Option(int, "延遲時間(分)", min_value=0, default=0, name="countdown_min"),
        Option(int, "延遲時間(秒)", min_value=0, default=0, name="countdown_sec"),
        Option(bool, "是否清除恐龍", default=False, name="cleardino")
    ]
    servers_key_option = Option(str, "伺服器ID", name="unique_key", choices=[
        OptionChoice(name=server.config.display_name, value=server.config.unique_key)
        for server in ARK_SERVERS.values()
    ])
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.last_status = {}
    
    def __count_statuscode(
            self,
            server_status: bool,
            rcon_status: bool,
            last_status: Optional[None]=None
        ) -> int:
            if last_status == None:
                last_status = 1
            # 正常運行
            if server_status and rcon_status: return 0
            elif server_status:
                # 啟動中
                if last_status == 1 or last_status == 2: return 2
                # RCON 失去連線
                return 3
            # 完全中斷
            return 1
    
    def __get_server(self, ctx: BridgeContext) -> Optional[ARKServer]:
        channel_id = ctx.channel.id
        servers = list(filter(
            lambda server: server.config.discord_config.text_channel_id == channel_id,
            ARK_SERVERS.values()
        ))
        if len(servers) == 0:
            return None
        return servers[0]
    
    async def __check_server(self, ctx: BridgeContext, server: Optional[ARKServer]):
        if server == None:
            await response(ctx=ctx, content="You are not in a server channel.")
            return False
        if await server.check_opera():
            await response(ctx=ctx, content="An Operation Already Running.")
            return False
        if not server.server_status():
            await response(ctx=ctx, content="Server Not Running.")
            return False
        if not await server.rcon_status():
            await response(ctx=ctx, content="RCON Not Connected.")
            return False
        return True
    
    async def __check_user(self, ctx: BridgeContext):
        if str(DISCORD_CONFIG.rcon_role) in map(lambda role: str(role.id), ctx.author.roles):
            return True
        await response(ctx=ctx, content="Permission Denied.")
        return False
    
    @bridge_group()
    async def ark(self, ctx: BridgeContext):
        ...
    
    @ark.command(name="command", description="執行ARK指令。",)
    async def command(
        self,
        ctx: BridgeContext,
        content: Option(input_type=str, description="指令")
    ):
        if not await self.__check_user(ctx=ctx):
            return
        server = self.__get_server(ctx=ctx)
        if await self.__check_server(ctx=ctx, server=server):
            result = await server.run(content)
            await response(ctx=ctx, content=result)
    
    @ark.command(name="save", description="存檔", options=operation_options)
    async def save(
        self,
        ctx: BridgeContext,
        countdown_min: int=0,
        countdown_sec: int=0,
        cleardino: bool=False,
    ):
        if not await self.__check_user(ctx=ctx):
            return
        server = self.__get_server(ctx=ctx)
        if await self.__check_server(ctx=ctx, server=server):
            await response(ctx=ctx, content="Save Successful.")
            countdown = int(countdown_min) * 60 + int(countdown_sec)
            cleardino = bool(cleardino)
            await server.save(countdown=countdown, clear_dino=cleardino)
    
    @ark.command(name="stop", description="關閉伺服器", options=operation_options)
    async def stop(
        self,
        ctx: BridgeContext,
        countdown_min: int=0,
        countdown_sec: int=0,
        cleardino: bool=False,
    ):
        if not await self.__check_user(ctx=ctx):
            return
        server = self.__get_server(ctx=ctx)
        if await self.__check_server(ctx=ctx, server=server):
            await response(ctx=ctx, content="Stop Successful.")
            countdown = int(countdown_min) * 60 + int(countdown_sec)
            cleardino = bool(cleardino)
            await server.stop(countdown=countdown, clear_dino=cleardino)
    
    @ark.command(name="restart", description="重啟伺服器", options=operation_options)
    async def restart(
        self,
        ctx: BridgeContext,
        countdown_min: int=0,
        countdown_sec: int=0,
        cleardino: bool=False,
    ):
        if not await self.__check_user(ctx=ctx):
            return
        server = self.__get_server(ctx=ctx)
        if await self.__check_server(ctx=ctx, server=server):
            await response(ctx=ctx, content="Restart Successful.")
            countdown = int(countdown_min) * 60 + int(countdown_sec)
            cleardino = bool(cleardino)
            await server.restart(countdown=countdown, clear_dino=cleardino)
    
    @ark.command(name="cancel", description="取消重啟/存檔/關閉")
    async def cancel(
        self,
        ctx: BridgeContext,
    ):
        if not await self.__check_user(ctx=ctx):
            return
        server = self.__get_server(ctx=ctx)
        if server == None:
            await response(ctx=ctx, content="You are not in a server channel.")
        else:
            await server.cancel()
            await response(ctx=ctx, content="Cancel Successful.")
    
    @ark.command(name="start", description="啟動伺服器")
    async def start(
        self,
        ctx: BridgeContext,
    ):
        if not await self.__check_user(ctx=ctx):
            return
        server = self.__get_server(ctx=ctx)
        if server == None:
            await response(ctx=ctx, content="You are not in a server channel.")
        else:
            if server.server_status():
                await response(ctx=ctx, content="Server Already Running.")
            else:
                await response(ctx=ctx, content="Server Started.")
                await server.start()
    
    @ark.command(name="status", description="伺服器狀態", options=[servers_key_option])
    async def status(
        self,
        ctx: BridgeContext,
        unique_key: str
    ):
        server = ARK_SERVERS.get(unique_key)
        if server == None:
            await response(ctx=ctx, content="Server Not Found.")
        else:
            mes = await response(ctx=ctx, content="Querying...")
            loop = get_event_loop()
            status_code = self.__count_statuscode(
                await loop.run_in_executor(None, server.server_status),
                await server.rcon_status(),
                self.last_status.get(unique_key)
            )
            if status_code != self.last_status.get(unique_key):
                # 更新狀態
                self.last_status[unique_key] = status_code
            result = "伺服器狀態: "
            if status_code == 0:
                result += STATUS_MESSAGES.running
            elif status_code == 1:
                result += STATUS_MESSAGES.stopped
            elif status_code == 2:
                result += STATUS_MESSAGES.starting
            elif status_code == 3:
                result += STATUS_MESSAGES.rcon_disconnect
            if type(mes) == Message:
                await mes.edit(content=result)
            else:
                await mes.edit_original_response(content=result)
            
    
def setup(bot: Bot):
    bot.add_cog(ArkCog(bot))