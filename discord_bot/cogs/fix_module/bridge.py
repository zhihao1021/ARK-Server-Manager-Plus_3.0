from discord.ext.bridge import (
    BridgeContext,
    BridgeCommand,
    BridgeCommandGroup,
    BridgeExtCommand,
    BridgeSlashCommand,
)

class NewBridgeCommandGroup(BridgeCommandGroup):
    def __init__(self, callback, *args, **kwargs):
        super().__init__(callback, *args, **kwargs)
        self.parent = kwargs.pop("parent", None)
        self.name = kwargs.pop("name", self.ext_variant.name)
    
    def command(self, *args, **kwargs):
        def wrap(callback):
            slash = self.slash_variant.command(
                *args,
                **kwargs,
                cls=BridgeSlashCommand,
            )(callback)
            ext = self.ext_variant.command(
                *args,
                **kwargs,
                cls=BridgeExtCommand,
            )(callback)
            command = NewBridgeCommand(
                callback, parent=self, slash_variant=slash, ext_variant=ext
            )
            self.subcommands.append(command)
            return command
        return wrap

class NewBridgeCommand(BridgeCommand):
    def __init__(self, callback, **kwargs):
        super().__init__(callback, **kwargs)
        self.name = kwargs.pop("name", self.ext_variant.name)

def bridge_group(**kwargs):
    def decorator(callback):
        return NewBridgeCommandGroup(callback, **kwargs)
    return decorator

def bridge_command(**kwargs):
    def decorator(callback):
        return NewBridgeCommand(callback, **kwargs)
    return decorator

async def response(ctx: BridgeContext, content: str):
    if ctx.is_app:
        return await ctx.respond(content, ephemeral=True)
    else:
        return await ctx.respond(content, mention_author=False)
