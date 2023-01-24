from .cogs.config import ADMIN_PERMISSION
from .cogs.fix_module import bridge_group, response

from modules import Json

from typing import Union, Iterable

from discord import Cog
from discord.errors import ApplicationCommandInvokeError
from discord.ext.bridge import Bot, BridgeContext

class CogMangerCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
    
    @bridge_group(default_member_permissions=ADMIN_PERMISSION)
    async def cog(self, ctx: BridgeContext):
        ...
    
    @cog.command(name="list")
    async def list(self, ctx: BridgeContext):
        all_cog_names = cogs_data()[1].keys()
        activate_cog_names = self.bot.cogs.keys()

        result = [
            "All Cog:",
            "```",
            "\n".join(all_cog_names),
            "```",
            "",
            "Activate Cogs:",
            "```",
            "\n".join(activate_cog_names),
            "```"
        ]
        result = "\n".join(result)

        await response(ctx=ctx, content=result)

    @cog.command(name="load")
    async def load(self, ctx: BridgeContext, cog_name: str):
        package, data = cogs_data()
        cog_path = data.get(cog_name)
        if cog_path == None:
            result = f"Cog `{cog_name}` Not Found."
        else:
            if cog_name not in self.bot.cogs.keys():
                self.bot.unload_extension(gen_cog_path(cog_path, package))
                result = f"Unload `{cog_name}` Successful."
            else:
                result = f"Cog `{cog_name}` Already Activated."
        
        await response(ctx=ctx, content=result)
    
    @cog.command(name="unload")
    async def unload(self, ctx: BridgeContext, cog_name: str):
        package, data = cogs_data()
        cog_path = data.get(cog_name)
        if cog_path == None:
            result = f"Cog `{cog_name}` Not Found."
        else:
            if cog_name in self.bot.cogs.keys():
                self.bot.unload_extension(gen_cog_path(cog_path, package))
                result = f"Unload `{cog_name}` Successful."
            else:
                result = f"Cog `{cog_name}` Not Activated."
        
        await response(ctx=ctx, content=result)
    
    @cog.command(name="reload")
    async def reload(self, ctx: BridgeContext, cog_name: str):
        package, data = cogs_data()
        cog_path = data.get(cog_name)
        if cog_path == None:
            result = f"Cog `{cog_name}` Not Found."
        else:
            if cog_name in self.bot.cogs.keys():
                self.bot.reload_extension(gen_cog_path(cog_path, package))
                result = f"Reload `{cog_name}` Successful."
            else:
                result = f"Cog `{cog_name}` Not Activated."
        
        await response(ctx=ctx, content=result)
    
    @cog.command(name="error")
    async def error(self, ctx: BridgeContext):
        await response(ctx=ctx, content="Raise RuntimeError.")
        raise RuntimeError("Error")
    
    # async def cog_command_error(self, ctx: BridgeContext, error: ApplicationCommandInvokeError):
    #     from traceback import format_exception
    #     res = "".join(format_exception(error))
    #     await response(ctx=ctx, content="Error:```" + res + "```")

def cogs_data() -> tuple[str, dict[str, str]]:
    data = Json.load("discord_bot/cogs_data.json")
    return data["package"], data["cogs"]

def gen_cog_path(cog: Union[str, Iterable], package: str) -> Union[str, tuple]:
    if type(cog) == str:
        return ".".join((package, cog))
    return tuple(map(lambda cog: ".".join((package, cog)), cog))

def setup(bot: Bot):
    bot.add_cog(CogMangerCog(bot))
    package, data = cogs_data()
    bot.load_extensions(*gen_cog_path(data.values(), package))
