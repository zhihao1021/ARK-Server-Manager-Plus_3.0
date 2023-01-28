from .rcon_connection import RCONSession

from configs import ARKTimeData, ARKServerConfig, BROADCAST_MESSAGES, DISCORD_CONFIG, FILTERS, TIMEZONE, SERVERS
from modules import Json, Thread
from swap import DISCORD_CHAT_QUEUE

from asyncio import CancelledError, create_task, gather, get_event_loop, new_event_loop, Queue, sleep as asleep, Task
from datetime import datetime, time, timedelta
from logging import getLogger
from os import system
from os.path import abspath, join, splitext
from shutil import copyfile
from subprocess import run, PIPE
from traceback import format_exception
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
        def future_day(time_data: ARKTimeData) -> datetime:
            time_ = time_data.time
            result = datetime.combine(now_datetime.date(), time_)
            now_time = now_datetime.time()
            now_time = now_time.replace(tzinfo=now_datetime.tzinfo)
            if time_ < now_time:
                result += timedelta(days=1)
            return result
        while True:
            try:
                # 檢查狀態
                accessable = await self.check_accessable()
                need_start = not self.server_status()
                if not accessable and not need_start:
                    await asleep(10)
                    continue
                # 目前時間
                now_datetime = datetime.now(tz=TIMEZONE)
                # 下次存檔時間資料
                save_table = sorted(
                    self.config.time_table,
                    key=future_day
                )
                if not need_start:
                    save_table = filter(lambda time_date: time_date.method != "start", save_table)
                else:
                    save_table = filter(lambda time_date: time_date.method == "start", save_table)
                try:
                    next_save = tuple(save_table)[0]
                except IndexError:
                    await asleep(10)
                    continue
                # 計算時間差
                target_time = future_day(next_save)
                remain_time: timedelta = target_time - now_datetime
                __cancel = False
                while remain_time.total_seconds() > 305:
                    __accessable = await self.check_accessable()
                    __need_start = not self.server_status()
                    if accessable !=  __accessable or need_start != __need_start:
                        __cancel = True
                        break
                    remain_time = target_time - datetime.now(tz=TIMEZONE)
                if __cancel:
                    continue
                remain_time = target_time - datetime.now(tz=TIMEZONE)
                self.__logger.info(f"[Auto Save]Remain {remain_time.total_seconds()}s to {next_save.method.capitalize()}.")
                success = True
                if next_save.method == "start":
                    success = await self.start()
                elif next_save.method == "save":
                    success = await self.save(countdown=remain_time.total_seconds(), clear_dino=next_save.clear_dino)
                elif next_save.method == "stop":
                    success = self.stop(countdown=remain_time.total_seconds(), clear_dino=next_save.clear_dino)
                elif next_save.method == "restart":
                    success = self.restart(countdown=remain_time.total_seconds(), clear_dino=next_save.clear_dino)
                self.__logger.info(f"[Auto Save]{next_save.method.capitalize()} Finish.")
                if success:
                    await self.__add_to_chat(f"[Auto Save]{next_save.method.capitalize()} in {target_time.isoformat()} Successful.")
                else:
                    await self.__add_to_chat(f"[Auto Save]{next_save.method.capitalize()} in {target_time.isoformat()} Fail.")
                    remain_time = target_time - datetime.now(tz=TIMEZONE)
                    await asleep(remain_time.total_seconds() + 1)
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

    async def rcon_status(self, timeout: float=10):
        """
        檢查RCON是否已連線。
        """
        res = await self.rcon.run("test", timeout=timeout)
        return res != None

    def __check_pid(self, pid: int):
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
        result = map(self.__check_pid, all_pid)
        return True in result
    
    async def __save(self, countdown: int=0, clear_dino: bool=False, mode=0) -> bool:
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
            
            # 取得地圖檔案位置
            map_path = abspath(join(self.config.dir_path, "ShooterGame\\Saved\\SavedArks", self.config.file_name))
            # 儲存檔案
            if clear_dino:
                self.__logger.warning("Pre Save World.")
            else:
                self.__logger.warning("Save World.")
            await self.rcon.run("saveworld")
            if clear_dino:
                # 取得當前所有恐龍
                # await self.rcon.run("Slomo 0")
                self.__logger.warning("Clearing Dinos.")
                loop = get_event_loop()
                def __get_dinos():
                    res = run(f"dinos_reader/Test.exe \"{map_path}\"", stdout=PIPE, stderr=PIPE)
                    err = res.stderr
                    if type(err) == bytes:
                        err = err.decode()
                    return res.stdout, err
                # 讀取檔案
                try:
                    # 清除恐龍
                    res, err = await loop.run_in_executor(None, __get_dinos)
                    dino_classes: list[str] = Json.loads(res)
                    __tasks = [
                        create_task(self.rcon.run(f"DestroyWildDinoClasses \"{dino_class}\" 1", timeout=0), name="DestroyDino")
                        for dino_class in dino_classes
                    ]
                    await gather(*__tasks)
                    # 清除所有
                    await self.rcon.run("DestroyWildDinos")
                    # await self.rcon.run("Slomo 1")
                except:
                    # await self.__add_to_chat(message=f"<@&{DISCORD_CONFIG.rcon_role}> 讀取地圖檔失敗，建議檢查地圖檔。 (位置:`" + map_path + "`)")
                    await self.__add_to_chat(message=f"讀取地圖檔失敗，建議檢查地圖檔。 (位置:`" + map_path + "`)\nError Message: ```" + err + "```")
                    await self.__add_to_chat(message="Save Without Clear Dino...")
                    self.__logger.error("Read Map Error: " + str(err))
                    self.__logger.error("Save Without Clear Dino...")
            await self.rcon.run(f"broadcast {BROADCAST_MESSAGES.saved}")
            await self.__add_to_chat(message=BROADCAST_MESSAGES.saved)
            time_format = datetime.now(tz=TIMEZONE).replace(microsecond=0).isoformat().replace(":", "_")
            try:
                self.__logger.info("Backup Map File...")
                await self.__add_to_chat(message="Backup Map File...")
                copyfile(map_path, f"-{time_format}".join(splitext(map_path)))
            except Exception as __exc:
                mes = "".join(format_exception(__exc))
                self.__logger.error("Backup Failed: " + str(mes))
                await self.__add_to_chat(message=f"地圖檔備份失敗。\nError Message: ```" + mes + "```")
            if mode < 1:
                self.__logger.info("[Save]Finish.")
                return True
            # 關閉伺服器
            self.__logger.warning("Exit.")
            await self.rcon.run("doexit")
            if mode < 2:
                self.__logger.info("[Stop]Finish.")
                return True
            # 等待伺服器完全關閉
            while self.server_status():
                await asleep(1)
            # 重啟伺服器
            await self.start()
            self.__logger.info("[Restart]Finish.")
            return True
        except CancelledError:
            # await self.rcon.run("Slomo 1")
            for task in command_task:
                task.cancel()
            return False
    
    async def start(self) -> bool:
        """
        啟動伺服器。
        """
        if self.server_status():
            return False
        command_file = abspath(join(self.config.dir_path, "ShooterGame\\Saved\\Config\\WindowsServer\\RunServer.cmd"))
        async with aopen(command_file) as _file:
            command_line = await _file.read()
            command_line = command_line.strip()
        try:
            origin_str = list(filter(lambda s: s.startswith("MultiHome="), command_line.split("?")))[0]
            command_line = command_line.replace(origin_str, "MultiHome=0.0.0.0")
        except IndexError:
            command_line = command_line.replace("listen?", "listen?MultiHome=0.0.0.0?")
        while command_line.startswith("start "):
            command_line = command_line.removeprefix("start ")
        async with aopen(command_file, mode="w") as _file:
            await _file.write("start " + command_line)
        system("start cmd /c \"" + command_file + "\"")
        await self.__add_to_chat(message=BROADCAST_MESSAGES.start)
        self.__logger.warning("Start Server.")
        return True
    
    async def check_opera(self) -> bool:
        """
        檢查是否有存檔程序在執行中。
        """
        if self.__operation == None:
            return False
        if self.__operation.done():
            return False
        return True
    
    async def check_accessable(self) -> bool:
        """
        檢查伺服器是否在正常運作中。
        """
        if await self.check_opera():
            return False
        if not self.server_status():
            return False
        if not await self.rcon_status():
            return False
        return True
    
    async def cancel(self) -> bool:
        """
        取消關機/重啟。
        """
        if not await self.check_opera():
            return False
        self.__operation.cancel()
        return True
    
    async def save(self, countdown: int=0, clear_dino: bool=False) -> bool:
        """
        存檔。
        """
        if not await self.check_accessable():
            return False
        self.__operation = create_task(self.__save(countdown=countdown, clear_dino=clear_dino, mode=0))
        await gather(self.__operation)
        return True
    
    async def stop(self, countdown: int=0, clear_dino: bool=False) -> bool:
        """
        關機。
        """
        if not await self.check_accessable():
            return False
        self.__operation = create_task(self.__save(countdown=countdown, clear_dino=clear_dino, mode=1))
        await gather(self.__operation)
        return True

    async def restart(self, countdown: int=0, clear_dino: bool=False) -> bool:
        """
        重啟。
        """
        if not await self.check_accessable():
            return False
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
