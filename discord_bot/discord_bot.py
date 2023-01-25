from ark_module import ARK_SERVERS, ARKServer
from configs import DISCORD_CONFIG, STATUS_MESSAGES
from modules import Thread
from swap import DISCORD_CHAT_QUEUE

from asyncio import all_tasks, CancelledError, create_task, gather, get_event_loop, sleep as asleep
from io import BytesIO
from logging import getLogger
from traceback import format_exception, format_exc
from typing import Optional

from discord import ApplicationContext, DiscordException, File, Intents
from discord.ext.bridge import Bot
from discord.ext.commands import CommandError, Context, when_mentioned_or

class DiscordBot(Bot):
    def __init__(self, *args, **kwargs):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(*args, command_prefix=when_mentioned_or(*DISCORD_CONFIG.prefixs), intents=intents, **kwargs)

        self.__logger = getLogger("discord")
        self.__thread = None
        self.__first_connect = True

        self.load_extension("discord_bot.cog_manger")

    async def on_ready(self):
        if self.__first_connect:
            self.__first_connect = False
            self.__logger.warning(f"Discord Bot {self.user} Start.")

            self.loop = get_event_loop()
            self.loop.create_task(self.update_status_channel())
            self.loop.create_task(self.sync_chat_channel())
        else:
            self.__logger.warning(f"Discord Bot {self.user} Reconnect.")
    
    async def on_disconnect(self):
        self.__logger.warning(f"Discord Bot {self.user} Disconnect.")

    async def update_status_channel(self):
        """
        更新狀態頻道。
        """
        self.__logger.info("Start `update_status_channel`.")
        def count_statuscode(
            server_status: bool,
            rcon_status: bool,
            last_status: Optional[int]=None
        ) -> int:
            # 正常運行
            if last_status == None:
                last_status = 1
            if server_status and rcon_status: return 0
            elif server_status:
                # 啟動中
                if last_status == 1 or last_status == 2: return 2
                # RCON 失去連線
                return 3
            # 完全中斷
            return 1
        async def update(unique_key: str, server: ARKServer):
            # 取得伺服器狀態
            status_code = count_statuscode(
                await self.loop.run_in_executor(None, server.server_status),
                await server.rcon_status(),
                last_status.get(unique_key)
            )
            # 檢查伺服器狀態是否有改變
            t = t_dict.get(unique_key, 0)
            if status_code != last_status.get(unique_key):
                t += 1
            else:
                t = 0
            if t > 5:
                t = 0
                # 更新狀態
                last_status[unique_key] = status_code
                # 發送狀態
                result = "伺服器狀態: "
                if status_code == 0:
                    result += STATUS_MESSAGES.running
                elif status_code == 1:
                    result += STATUS_MESSAGES.stopped
                elif status_code == 2:
                    result += STATUS_MESSAGES.starting
                elif status_code == 3:
                    result += STATUS_MESSAGES.rcon_disconnect
                channel = self.get_channel(ARK_SERVERS[unique_key].config.discord_config.text_channel_id)
                await channel.send(result)
            t_dict[unique_key] = t

        last_status = {}
        t_dict = {}
        while True:
            try:
                tasks = [
                    create_task(update(unique_key=unique_key, server=server))
                    for unique_key, server in ARK_SERVERS.items()
                ]
                await gather(*tasks, return_exceptions=True)
                await asleep(1)
            except CancelledError:
                print("Status be Cancel")
                return
    
    async def sync_chat_channel(self):
        """
        更新文字頻道。
        """
        self.__logger.info("Start `sync_chat_channel`.")
        while True:
            try:
                if DISCORD_CHAT_QUEUE.empty():
                    await asleep(0.1)
                    continue
                data: dict[str, str] = await DISCORD_CHAT_QUEUE.get()
                unique_key, content = data.values()
                channel = self.get_channel(ARK_SERVERS[unique_key].config.discord_config.text_channel_id)
                if len(content) >= 2000:
                    io = BytesIO(content.encode())
                    await channel.send(file=File(io, filename="message.txt"))
                else:
                    await channel.send(content=content)
            except CancelledError:
                return
    
    # Log Handler
    async def on_command(self, ctx: Context):
        self.__logger.info(f"[Command] {ctx.author}: {ctx.message.content}")
    async def on_application_command(self, ctx: ApplicationContext):
        self.__logger.info(f"[Command] {ctx.author}: {ctx.command.qualified_name}")
    
    # Error Handler
    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        message = f"Error in {event_method}\n"
        message += format_exc()
        self.__logger.error(message)
    async def on_command_error(self, ctx: Context, exception: CommandError) -> None:
        res = "".join(format_exception(exception))
        self.__logger.error(res)
        error_message = "Error:```" + res + "```"
        if len(error_message) >= 2000:
            io = BytesIO(res.encode())
            await ctx.reply(content="Error:", file=File(io, filename="error.log"))
        else:
            await ctx.reply(content=error_message, mention_author=False)
    async def on_application_command_error(self, ctx: ApplicationContext, exception: DiscordException) -> None:
        res = "".join(format_exception(exception))
        self.__logger.error(res)
        error_message = "Error:```" + res + "```"
        if len(error_message) >= 2000:
            io = BytesIO(res.encode())
            await ctx.respond(content="Error:", file=File(io, filename="error.log"), ephemeral=True)
        else:
            await ctx.respond(content=error_message, ephemeral=True)
    
    def __thread_job(self):
        try:
            self.run(token=DISCORD_CONFIG.token)
        except SystemExit:
            for task in all_tasks(self.loop):
                task.cancel()
            self.loop.stop()
        self.loop.close()

    def startup(self):
        if self.__thread != None:
            return
        self.__thread = Thread(target=self.__thread_job, name="Discord")
        self.__thread.start()

