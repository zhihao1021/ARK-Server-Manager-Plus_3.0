from ark_module import startup, ARK_SERVERS
from discord_bot import DiscordBot
from configs import logger_init

from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
from os import getpid
from os.path import isfile
from platform import system

from psutil import NoSuchProcess, Process

if __name__ == "__main__":
    if isfile("PID"):
        with open("PID", mode="r") as pid_file:
            last_pid = int(pid_file.read().strip())
        try:
            print(f"Waiting For PID: {last_pid}")
            Process(last_pid).wait()
        except NoSuchProcess:
            pass

    if system() == "Windows":
        set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    logger_init()
    pid = getpid()
    with open("PID", mode="w") as pid_file:
        pid_file.write(str(pid))
    
    startup()
    bot = DiscordBot()
    bot.startup()

    from time import sleep, time
    while True:
        sleep(1)
