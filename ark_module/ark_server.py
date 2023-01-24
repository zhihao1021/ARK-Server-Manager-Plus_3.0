from .rcon_connection import RCONSession

from configs import ARKServerConfig, BROADCAST_MESSAGES, FILTERS, TIMEZONE, SERVERS
from modules import Json, Thread
from swap import DISCORD_CHAT_QUEUE

from asyncio import CancelledError, create_task, gather, get_event_loop, new_event_loop, Queue, sleep as asleep, Task
from datetime import datetime, time, timedelta
from logging import getLogger
from os import system
from os.path import abspath, join
from subprocess import run, PIPE
from typing import Optional

from aiofiles import open as aopen
from psutil import AccessDenied, NoSuchProcess, pids, Process

CHAT_LISTENER: list[Queue] = [
    DISCORD_CHAT_QUEUE,
]

class ARKServer:
    config: ARKServerConfig
    def __init__(self, config: ARKServerConfig) -> None:
        self.config = config

        self.rcon = RCONSession(
            **self.config.rcon_config.dict()
        )
        self.__logger = getLogger(self.config.logger_name)

        self.__operation: Optional[Task] = None
        self.__pid = None
        
        target = join(self.config.dir_path, "ShooterGame\\Binaries\\Win64\\ShooterGameServer.exe")
        self.__target = abspath(target)
    
    async def startup_background(self):
        # 背景作業
        tasks = [
            create_task(self.__update_chat()),
            create_task(self.__auto_save()),
        ]
        self.__logger.info("Background Task Startup.")
        await gather(*tasks)
    
    async def __add_to_chat(self, message: str):
        """
        將訊息新增至監聽清單。
        """
        message = "\n".join(map(lambda sub: f"[{self.config.display_name}]"+sub, message.split("\n")))
        for listener in CHAT_LISTENER:
            await listener.put({
                "unique-key": self.config.unique_key,
                "content": message.strip()
            })

    async def __update_chat(self):
        """
        取得聊天訊息，並送到眝列。

        資料格式: {
            "unique-key": "",
            "content": "",
        }
        """
        while True:
            try:
                # 取得訊息
                res = await self.rcon.run("GetChat")
                # 判斷訊息是否為空
                if res == "" or res == None:
                    await asleep(1)
                    continue
                self.__logger.info(f"[GetChat]{res}")
                # 過濾訊息
                if res.startswith(FILTERS.startswith) or res.endswith(FILTERS.endswith):
                    continue
                if True in map(lambda sub_str: sub_str in res, FILTERS.include):
                    continue
                # 修飾訊息

                await self.__add_to_chat(res.strip())
            except CancelledError:
                return
    
    async def __auto_save(self):
        """
        自動儲存。
        """
        def future_day(now_datetime: datetime, time_: time) -> datetime:
            result = datetime.combine(now_datetime.date(), time_)
            if time_ > now_datetime.time():
                return result
            return result + timedelta(days=1)
        while True:
            try:
                # 檢查是否需要重啟
                if await self.check_opera():
                    await asleep(10)
                    continue
                if not self.server_status():
                    await asleep(10)
                    continue
                if not await self.rcon_status():
                    await asleep(10)
                    continue
                # 目前時間
                now_datetime = datetime.now()
                # 下次存檔時間資料
                __next_save = sorted(
                    self.config.save_time,
                    key=lambda timedata: future_day(now_datetime, time_=timedata.time)
                )[0]
                # 下次重啟時間資料
                __next_restart = sorted(
                    self.config.restart_time,
                    key=lambda timedata: future_day(now_datetime, time_=timedata.time)
                )[0]
                # 時間差
                __save_delta = future_day(now_datetime, __next_save.time) - now_datetime
                __restart_delta = future_day(now_datetime, __next_restart.time) - now_datetime
                # 計算並等待時間差
                if __save_delta < __restart_delta:
                    await asleep(__save_delta.total_seconds() - 305)
                    now_datetime = datetime.now()
                    __save_delta = future_day(now_datetime, __next_save.time) - now_datetime
                    self.__logger.info(f"[Auto Save]Remain {__save_delta.total_seconds()}s.")
                    await self.save(countdown=__save_delta.total_seconds(), clear_dino=__next_save.clear_dino)
                else:
                    await asleep(__restart_delta.total_seconds() - 305)
                    now_datetime = datetime.now()
                    __restart_delta = future_day(now_datetime, __next_restart.time) - now_datetime
                    self.__logger.info(f"[Auto Restart]Remain {__restart_delta.total_seconds()}s.")
                    await self.restart(countdown=__restart_delta.total_seconds(), clear_dino=__next_restart.clear_dino)
                await asleep(1)
            except CancelledError:
                return
    
    async def run(self, command: str) -> str:
        if type(command) != str:
            try: command = str(command)
            except: return ""
        result = await self.rcon.run(command)
        if result == None:
            result = ""
        self.__logger.info(f"[Command]{command} Reply:{result}")
        return result

    async def rcon_status(self, timeout: float=5):
        """
        檢查RCON是否已連線。
        """
        res = await self.rcon.run("test", timeout=timeout)
        return res != None

    def __check(self, pid: int):
        try:
            res = self.__target in Process(pid).cmdline()
            if res:
                self.__pid = pid
                return True
            return False
        except (AccessDenied, NoSuchProcess):
            return False

    def server_status(self):
        """
        檢查伺服器是否運作中。
        """
        if self.__pid != None:
            try:
                process = Process(self.__pid)
                if self.__target in process.cmdline():
                    return True
            except NoSuchProcess:
                pass
        all_pid = pids()
        result = map(self.__check, all_pid)
        return True in result
    
    async def __save(self, countdown: int=0, clear_dino: bool=False, mode=0):
        if mode == 0:
            message = BROADCAST_MESSAGES.save
        elif mode == 1:
            message = BROADCAST_MESSAGES.stop
        elif mode == 2:
            message = BROADCAST_MESSAGES.restart
        command_task: list[Task] = []
        countdown = max(0, int(countdown))
        
        try:
            # 倒數
            while countdown > 0:
                if countdown % 60 == 0 and (minute := countdown // 60) <= 5:
                    mes = message.replace("$T", str(minute))
                    await self.rcon.run(f"broadcast {mes}")
                    await self.__add_to_chat(message=mes)
                    self.__logger.info(f"[{['Save', 'Stop', 'Restart'][mode]}]Remain {countdown}s.")
                countdown -= 1
                await asleep(1)
            await self.rcon.run(f"broadcast {BROADCAST_MESSAGES.saving}")
            await self.__add_to_chat(message=BROADCAST_MESSAGES.saving)
            
            if clear_dino:
                # 取得當前所有恐龍
                await self.rcon.run("Slomo 0")
                self.__logger.warning("Pre Save World.")
                await self.rcon.run("saveworld")
                self.__logger.warning("Clearing Dinos.")
                # 取得地圖檔案位置
                map_path = abspath(join(self.config.dir_path, "ShooterGame\\Saved\\SavedArks", self.config.file_name))
                loop = get_event_loop()
                def __get_dinos():
                    res = run(f"dinos_reader/Test.exe \"{map_path}\"", stdout=PIPE)
                    return res.stdout
                # 讀取檔案
                res = await loop.run_in_executor(None, __get_dinos)
                dino_classes: list[str] = Json.loads(res)
                # 清除恐龍
                __tasks = [
                    create_task(self.rcon.run(f"DestroyWildDinoClasses \"{dino_class}\" 1", timeout=0), name="DestroyDino")
                    for dino_class in dino_classes
                ]
                await gather(*__tasks)
                # 清除所有
                await self.rcon.run("DestroyWildDinos")
                await self.rcon.run("Slomo 1")
            # 儲存檔案
            self.__logger.warning("Save World.")
            await self.rcon.run("saveworld")
            await self.rcon.run(f"broadcast {BROADCAST_MESSAGES.saved}")
            await self.__add_to_chat(message=BROADCAST_MESSAGES.saved)
            if mode < 1:
                self.__logger.info("[Save]Finish.")
                return
            # 關閉伺服器
            self.__logger.warning("Exit.")
            await self.rcon.run("doexit")
            if mode < 2:
                self.__logger.info("[Stop]Finish.")
                return
            # 等待伺服器完全關閉
            while self.server_status():
                await asleep(1)
            await asleep(5)
            # 重啟伺服器
            await self.start()
            self.__logger.info("[Restart]Finish.")
        except CancelledError:
            await self.rcon.run("Slomo 1")
            for task in command_task:
                task.cancel()
            return
    
    async def start(self):
        """
        啟動伺服器。
        """
        if self.server_status():
            return
        command_file = abspath(join(self.config.dir_path, "ShooterGame\\Saved\\Config\\WindowsServer\\RunServer.cmd"))
        async with aopen(command_file) as _file:
            command_line = await _file.read()
            command_line = command_line.strip()
        origin_str = list(filter(lambda s: s.startswith("MultiHome="), command_line.split("?")))[0]
        command_line = command_line.replace(origin_str, "MultiHome=0.0.0.0")
        while command_line.startswith("start "):
            command_line = command_line.removeprefix("start ")
        async with aopen(command_file, mode="w") as _file:
            await _file.write("start " + command_line)
        system("start cmd /c \"" + command_file + "\"")
        await self.__add_to_chat(message=BROADCAST_MESSAGES.start)
        self.__logger.warning("Start Server.")
    
    async def check_opera(self):
        """
        檢查是否有程序在執行中。
        """
        if self.__operation == None:
            return False
        if self.__operation.done():
            return False
        return True
    
    async def cancel(self):
        """
        取消關機/重啟。
        """
        if await self.check_opera():
            return
        self.__operation.cancel()
    
    async def save(self, countdown: int=0, clear_dino: bool=False):
        """
        存檔。
        """
        if await self.check_opera():
            return
        if not self.server_status():
            return
        if not await self.rcon_status():
            return
        self.__operation = create_task(self.__save(countdown=countdown, clear_dino=clear_dino, mode=0))
        await gather(self.__operation)
    
    async def stop(self, countdown: int=0, clear_dino: bool=False):
        """
        關機。
        """
        if await self.check_opera():
            return
        if not self.server_status():
            return
        if not await self.rcon_status():
            return
        self.__operation = create_task(self.__save(countdown=countdown, clear_dino=clear_dino, mode=1))
        await gather(self.__operation)

    async def restart(self, countdown: int=0, clear_dino: bool=False):
        """
        重啟。
        """
        if await self.check_opera():
            return
        if not self.server_status():
            return
        if not await self.rcon_status():
            return
        self.__operation = create_task(self.__save(countdown=countdown, clear_dino=clear_dino, mode=2))
        await gather(self.__operation)

def __thread_job(ark_servers: dict[str, ARKServer]):
    loop = new_event_loop()
    tasks: list[Task] = list(map(
        lambda server: loop.create_task(server.startup_background()),
        ark_servers.values()
    ))
    try:
        loop.run_until_complete(gather(*tasks))
    except SystemExit:
        for task in tasks:
            task.cancel()
        loop.stop()
    loop.close()

ARK_SERVERS: dict[str, ARKServer] = {
    unique_key: ARKServer(server_config)
    for unique_key, server_config in SERVERS.items()
}
thread = None

def startup():
    global thread
    if thread != None:
        return
    thread = Thread(target=__thread_job, name="ARK Servers", args=(ARK_SERVERS,))
    thread.start()
