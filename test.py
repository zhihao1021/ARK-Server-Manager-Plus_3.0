# from discord_bot import DiscordBot

# bot = DiscordBot()
# bot.startup()
# input()

from asyncio import all_tasks, new_event_loop, get_event_loop, sleep, set_event_loop_policy, WindowsSelectorEventLoopPolicy, CancelledError, Task

async def main():
    try:
        while True:
            await sleep(1)
            print(2)
    except CancelledError:
        return

def job(task: Task):
    from time import sleep
    sleep(5)
    task.cancel()

if __name__ == "__main__":
    from threading import Thread
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())

    loop = new_event_loop()
    task = loop.create_task(main())
    Thread(target=job, args=(task,)).start()
    loop.run_until_complete(task)
    loop.close()
