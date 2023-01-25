from asyncio import CancelledError, create_task, gather, sleep as asleep
from logging import getLogger
from traceback import format_exception
from typing import Optional

from rcon.source import rcon

class RCONSession:
    __logger = getLogger("rcon")
    host: str
    port: int
    password: str
    timeout: int
    def __init__(
        self,
        host: str,
        port: int,
        password: str,
        timeout: int=0,
    ) -> None:
        """
        新增一個RCON會話。
        
        :param host: 主機位置。
        :param port: 主機端口。
        :param passwd: 連接密碼。
        :param timeout: 連接超時。
        """
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout

        self.__timeout_task = None
    
    async def run(self, command: str, timeout: Optional[float]=None) -> Optional[str]:
        """
        發送指令。

        :param command: 指令。

        :return: str | None
        """
        tasks = (
            create_task(self.__timeout(timeout=timeout), name="RCON Timeout"),
            create_task(self.__run(command=command), name="RCON Run"),
        )
        self.__timeout_task = tasks[0]
        try:
            res = await gather(*tasks, return_exceptions=False)
            if res[1] == None:
                return None
            else:
                res = res[1].strip()
                if res == "Server received, But no response!!":
                    return ""
                return res
        except (TimeoutError, ConnectionRefusedError):
            for task in tasks:
                task.cancel()
            return None
        except Exception as exc:
            for task in tasks:
                task.cancel()
            error_meg = "".join(format_exception(exc))
            self.__logger.error(error_meg)
            return None
    
    async def __timeout(self, timeout: Optional[float]=None):
        if timeout == None:
            timeout = self.timeout
        if timeout <= 0: return
        try:
            while timeout > 1:
                await asleep(1)
                timeout -= 1
            await asleep(timeout)
            raise TimeoutError
        except CancelledError:
            return
        except TimeoutError:
            raise TimeoutError
        except Exception as exc:
            error_meg = "".join(format_exception(exc))
            self.__logger.error(error_meg)
            return None
    
    async def __run(self, command: str):
        try:
            res = await rcon(
                command,
                host=self.host,
                port=self.port,
                passwd=self.password
            )
            self.__timeout_task.cancel()
            return res.strip()
        except (ConnectionRefusedError, ConnectionResetError):
            await asleep(2)
            res = await self.__run(command=command)
            return res
        except CancelledError:
            return None
        except Exception as exc:
            error_meg = "".join(format_exception(exc))
            self.__logger.error(error_meg)
            return None
