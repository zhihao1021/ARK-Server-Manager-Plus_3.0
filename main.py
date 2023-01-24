from ark_module import startup, ARK_SERVERS
from discord_bot import DiscordBot
from configs import logger_init

from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
from platform import system

if __name__ == "__main__":
    if system() == "Windows":
        set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    logger_init()
    
    startup()
    bot = DiscordBot()
    bot.startup()

    from time import sleep, time
    sleep(5)
    from asyncio import new_event_loop
    loop = new_event_loop()
    timer = time()
    loop.run_until_complete(ARK_SERVERS["b971b0af"].rcon.run("test", timeout=2))
    print(time() - timer)
    loop.close()
    while True:
        sleep(1)
