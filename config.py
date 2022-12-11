from modules import Json
from os.path import isfile
from datetime import timedelta, timezone, time

class _ARKTimeData:
    TIME: time
    CLEAR_DINO: bool
    def __init__(self, time_isoformat: str, clear_dino: bool) -> None:
        self.TIME = time.fromisoformat(time_isoformat)
        self.CLEAR_DINO = clear_dino

class ARKServerConfig:
    UNIQUE_KEY: str
    DIR_PATH: str
    FILE_NAME: str
    DISPLAY_NAME: str
    RCON_ADDRESS: str
    RCON_PORT: int
    RCON_PASSWORD: str
    RCON_TIMEOUT: int
    DISCORD_TEXT_CHANNEL: int
    DISCORD_STATE_CHANNEL: int
    SAVE_TIME: list[_ARKTimeData]
    RESTART_TIME: list[_ARKTimeData]
    def __init__(self, config_path: str) -> None:
        data = Json.load(config_path)
        self.UNIQUE_KEY = data["unique-key"]
        self.DIR_PATH = data["dir_path"]
        self.FILE_NAME = data["file_name"]
        self.DISPLAY_NAME = data["display_name"]
        self.RCON_ADDRESS = data["rcon"]["address"]
        self.RCON_PORT = data["rcon"]["port"]
        self.RCON_PASSWORD = data["rcon"]["password"]
        self.RCON_TIMEOUT = data["rcon"]["timeout"]
        self.DISCORD_TEXT_CHANNEL = data["discord"]["text_channel_id"]
        self.DISCORD_STATE_CHANNEL = data["discord"]["state_channel_id"]
        self.SAVE_TIME = [_ARKTimeData(*dict_.values()) for dict_ in data["save_time"]]
        self.RESTART_TIME = [_ARKTimeData(*dict_.values()) for dict_ in data["restart_time"]]

CONFIG = {
    "web": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": True,
    },
    "sql": {
        "mysql": False,
        "host": "",
        "port": 0,
        "user": "",
        "password": "",
        "database": "data"
    },
    "servers": [
        # "servers-config/Server1.json",
    ],
    "ark_message_filter": {
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
        "endswith": []
    },
    "discord": {
        "token": "",
        "prefixs": [],
        "admin_role": 0
    },
    "broadcast": {
        "save": "伺服器將於 $TIME 分鐘後存檔。\nServer will save in $TIME min.",
        "stop": "伺服器將於 $TIME 分鐘後關閉。\nServer will shutdown in $TIME min.",
        "restart": "伺服器將於 $TIME 分鐘後重啟。\nServer will restart in $TIME min.",
        "saving": "儲存中...\nSaving..."
    },
    "state_message": {
        "running": "🟢 運作中",
        "stopped": "🔴 未開啟",
        "starting": "🔵 正在啟動中",
        "rcon_disconnect": "🟡 RCON失去連線",
        "network_disconnect": "🟠 對外失去連線"
    },
    "logging": {
        "level": "INFO",
        "backup_count": 3,
        "dir_path": "logs"
    },
    "low_battery": 30,
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

WEB_HOST: str = CONFIG["web"]["host"]
WEB_PORT: int = CONFIG["web"]["port"]
WEB_DEBUG: bool = CONFIG["web"]["debug"]

SQL_MYSQL: bool = CONFIG["sql"]["mysql"]
SQL_CONFIG: dict = {}
if SQL_MYSQL:
    SQL_CONFIG = {
        "host": CONFIG["sql"]["host"],
        "port": CONFIG["sql"]["port"],
        "user": CONFIG["sql"]["user"],
        "password": CONFIG["sql"]["password"],
        "database": CONFIG["sql"]["database"],
        "charset": "utf-8"
    }
else:
    SQL_CONFIG = {
        "database": f"{CONFIG['sql']['database']}.db",
    }
SQL_PORT: int = CONFIG["sql"]["port"]

_server_list: list[ARKServerConfig] = [ARKServerConfig(config_path) for config_path in CONFIG["servers"]]
SERVERS: dict[str, ARKServerConfig] = {asc.UNIQUE_KEY: asc for asc in _server_list}

ARK_FILTER_S: list[str] = CONFIG["ark_message_filter"]["startswith"]
ARK_FILTER_I: list[str] = CONFIG["ark_message_filter"]["include"]
ARK_FILTER_E: list[str] = CONFIG["ark_message_filter"]["endswith"]

DISCORD_TOKEN: str = CONFIG["discord"]["token"]
DISCORD_PREFIXS: list[str] = CONFIG["discord"]["prefixs"]
DISCORD_ADMIN: int = CONFIG["discord"]["admin_role"]

BROADCAST_SAVE: str = CONFIG["broadcast"]["save"]
BROADCAST_STOP: str = CONFIG["broadcast"]["stop"]
BROADCAST_RESTART: str = CONFIG["broadcast"]["restart"]
BROADCAST_SAVING: str = CONFIG["broadcast"]["saving"]

STATE_RUNNING: str = CONFIG["state_message"]["running"]
STATE_STOPPEN: str = CONFIG["state_message"]["stopped"]
STATE_STARTING: str = CONFIG["state_message"]["starting"]
STATE_RCON: str = CONFIG["state_message"]["rcon_disconnect"]
STATE_NET: str = CONFIG["state_message"]["network_disconnect"]

LOGGING_LEVEL: str = CONFIG["logging"]["level"]
LOGGING_BACKUP_COUNT: str = CONFIG["logging"]["backup_count"]
LOGGING_DIR_PATH: str = CONFIG["logging"]["dir_path"]

LOW_BATTERY: int = CONFIG["low_battery"]
TIMEZONE: timezone = timezone(timedelta(hours=CONFIG["timezone"]))

if SQL_MYSQL: pass
else:
    from sqlite3 import connect
    if not isfile("data.db"):
        db = connect(**SQL_CONFIG)
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
        