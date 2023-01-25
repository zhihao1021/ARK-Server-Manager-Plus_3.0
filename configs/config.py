from modules import Json

from datetime import timedelta, timezone, time
from logging import getLevelName, Logger
from os.path import isfile
from pydantic import BaseModel, Field, validator
from typing import Union, Optional

unique_key_list = []
# CRITICAL
# ERROR
# WARNING
# INFO
# DEBUG
# NOTSET
class LoggingConfig(BaseModel):
    stream_level: Union[int, str]=Field(20, alias="stream-level")
    file_level: Union[int, str]=Field(20, alias="file-level")
    backup_count: int=Field(3, alias="backup-count")
    file_name: str=Field(alias="file-name")
    dir_path: str=Field("logs", alias="dir-path")

    @validator("stream_level", "file_level")
    def level_name_validator(cls, value):
        if type(value) == int:
            if value in range(0, 51, 10):
                return value
        else:
            new_value = getLevelName(value)
            if type(new_value) == int:
                return new_value
        raise ValueError(f"Illegal level name: \"{value}\"")
    
    class Config:
        extra = "ignore"

class WebConfig(BaseModel):
    host: str
    port: int
    debug: bool

class DiscordConfig(BaseModel):
    token: str
    prefixs: list[str]
    rcon_role: int=Field(alias="rcon-role")

class _RCONConfig(BaseModel):
    host: str
    port: int
    password: str
    timeout: float

class _DiscordChannels(BaseModel):
    text_channel_id: int=Field(alias="text-channel-id")

class ARKTimeData(BaseModel):
    time: Union[time, str]
    clear_dino: bool=Field(False, alias="clear-dino")
    method: str
    
    @validator("time")
    def time_validator(cls, value):
        if type(value) != time:
            if type(value) != str:
                raise ValueError(f"Illegal time format: \"{value}\"")
            value = time.fromisoformat(value)
        if value.tzinfo == None:
            value = value.replace(tzinfo=TIMEZONE)
        return value
    
    @validator("method")
    def method_validator(cls, value: str):
        if value.lower() in ["restart", "save", "stop", "start"]:
            return value.lower()
        raise ValueError(f"Illegal method: \"{value}\"")

class ARKServerConfig(BaseModel):
    unique_key: str=Field(alias="unique-key")
    dir_path: str=Field(alias="dir-path")
    file_name: str=Field(alias="file-name")
    display_name: str=Field(alias="display-name")
    rcon_config: _RCONConfig=Field(alias="rcon")
    discord_config: _DiscordChannels=Field(alias="discord")
    time_table: list[ARKTimeData]=Field(alias="time-table")
    logging_config: LoggingConfig=Field(alias="logging")
    logger_name: Optional[str]=None

    @validator("unique_key")
    def unique_key_validator(cls, value):
        if value in unique_key_list:
            raise ValueError(f"Repeated unique-key: \"{value}\"")
        unique_key_list.append(value)
        return value

class MessageFilters(BaseModel):
    startswith: tuple[str, ...]
    include: tuple[str, ...]
    endswith: tuple[str, ...]

class BroadcastMessage(BaseModel):
    save: str
    stop: str
    start: str
    restart: str
    saving: str
    saved: str

class StatusMessage(BaseModel):
    running: str
    stopped: str
    starting: str
    rcon_disconnect: str=Field(alias="rcon-disconnect")
    network_disconnect: str=Field(alias="network-disconnect")

CONFIG: dict[str, Union[dict, str, int]] = {
    "web": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
    },
    "discord": {
        "token": "",
        "prefixs": [],
        "rcon-role": 0,
    },
    "servers": [
        "servers-config/Server-Example.json",
    ],
    "ark-message-filter": {
        "startswith": [
            "SERVER:",
            "管理員指令",
        ],
        "include": [
            "被自動摧毀了！",
            "has entered your zone.",
            "馴養了 一隻",
            "Souls were destroyed by ",
            "Soul was destroyed by ",
            "擊殺!",
            "已死亡!",
            "killed!",
            "你的部落 killed",
            "killed ，擊殺者：",
            "認養了",
            "摧毀了你的",
            "拆除了",
            "放生了'",
            "你的部落馴養了一隻",
            "冷藏了",
            "加入了部落！",
        ],
        "endswith": [],
    },
    "broadcast": {
        "save": "伺服器將於 $TIME 分鐘後存檔。\nServer will save in $TIME min.",
        "stop": "伺服器將於 $TIME 分鐘後關閉。\nServer will shutdown in $TIME min.",
        "start": "啟動伺服器。\nStart Server.",
        "restart": "伺服器將於 $TIME 分鐘後重啟。\nServer will restart in $TIME min.",
        "saving": "儲存中...\nSaving...",
        "saved": "儲存完成!\nWorld Saved!",
    },
    "status-message": {
        "running": "🟢 運作中",
        "stopped": "🔴 未開啟",
        "starting": "🔵 正在啟動中",
        "rcon-disconnect": "🟡 RCON失去連線",
        "network-disconnect": "🟠 對外失去連線",
    },
    "logging": {
        "main": {
            "stream-level": "INFO",
            "file-level": "INFO",
            "backup-count": 3,
            "file-name": "main",
            "dir-path": "logs",
        },
        "discord": {
            "stream-level": "WARNING",
            "file-level": "INFO",
            "backup-count": 3,
            "file-name": "discord",
            "dir-path": "logs",
        },
        "web": {
            "stream-level": "INFO",
            "file-level": "INFO",
            "backup-count": 3,
            "file-name": "web",
            "dir-path": "logs",
        },
        "rcon": {
            "stream-level": "INFO",
            "file-level": "INFO",
            "backup-count": 3,
            "file-name": "rcon",
            "dir-path": "logs",
        },
    },
    "database": "data.db",
    "low-battery": 30,
    "timezone": 8,
}

try:
    RAW_CONFIG: dict = Json.load("config.json")
    for key, value in RAW_CONFIG.items():
        if type(value) == dict:
            for s_key, s_value in value.items():
                CONFIG[key][s_key] = s_value
        else:
            CONFIG[key] = value
except: pass
finally:
    Json.dump("config.json", CONFIG)

TIMEZONE: timezone = timezone(timedelta(hours=CONFIG["timezone"]))

WEB_CONFIG = WebConfig(**CONFIG["web"])
DISCORD_CONFIG = DiscordConfig(**CONFIG["discord"])

__server_list: list[ARKServerConfig] = [
    ARKServerConfig(**Json.load(config_path)) for config_path in CONFIG["servers"]
]
SERVERS: dict[str, ARKServerConfig] = {
    ark_server_config.unique_key: ark_server_config
    for ark_server_config in __server_list
}

FILTERS = MessageFilters(**CONFIG["ark-message-filter"])
BROADCAST_MESSAGES = BroadcastMessage(**CONFIG["broadcast"])
STATUS_MESSAGES = StatusMessage(**CONFIG["status-message"])

SQL_FILE = CONFIG["database"]

LOGGING_CONFIG: dict[str, LoggingConfig] = {
    key: LoggingConfig(**value)
    for key, value in CONFIG["logging"].items()
}
for unique_key, server_config in SERVERS.items():
    server_config.logger_name = f"{server_config.display_name}-{unique_key}"
    LOGGING_CONFIG.update({
        server_config.logger_name: server_config.logging_config
    })

LOW_BATTERY: int = CONFIG["low-battery"]

with open("classlist") as _file:
    data = _file.read().strip()
DINO_CLASSES = data.split("\n")

if False:
    from sqlite3 import connect
    if not isfile("data.db"):
        db = connect(SQL_FILE)
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE "Users" (
                "discord_id" INTEGER NOT NULL UNIQUE,
                "account" TEXT NOT NULL UNIQUE,
                "password" TEXT NOT NULL,
                "token"	TEXT UNIQUE,
                PRIMARY KEY("discord_id")
            );
        """)
        db.commit()
        cursor.close()
        db.close()
