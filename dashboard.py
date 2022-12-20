from configs import *
from flask import Flask, render_template, url_for, redirect, request, make_response
import eventlet
from eventlet import wsgi
from modules import Thread
from flask_socketio import SocketIO, rooms, join_room
from hashlib import sha1
from modules import Json
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

def checkout_token(token: str) -> bool:
    """
    檢查上次登入時間，通過驗證則回傳`True`，反之則`False`。
    """
    database = connect(**SQL_CONFIG)
    cursor = database.cursor()

    # 查詢上次登入時間
    cursor.execute(f"SELECT discord_id FROM Users WHERE token=$1;", (token, ))
    discord_id = cursor.fetchone()
    
    # 關閉
    cursor.close()
    database.close()

    # 檢查是否有登入紀錄
    if discord_id == None: return False
    return True

@app.route("/")
def root():
    if not checkout_token(request.cookies.get("token", default="")):
        # 未通過驗證，導向至登入頁面。
        return redirect(url_for("login"))
    # 通過驗證，則導向至主頁面。
    return redirect(url_for("admin"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/admin")
def admin():
    if not checkout_token(request.cookies.get("token", default="")):
        # 未通過驗證，導向至登入頁面。
        return redirect(url_for("login"))
    return render_template("admin.html")

@app.route("/hello_world")
def hello_world():
    return render_template("Hello World.html")

@socketio.on("hello world", namespace="/")
def socket_hello_world(data):
    socketio.emit("hello world", f"Received: {data}")

@app.route("/api/get_token", methods=["POST", "GET"])
def api_get_token():
    """
    取得登入Token。
    """
    # 取得資料
    if request.is_json:
        data = request.get_json()
    else:
        data = {
            "account": request.values.get("account"),
            "password": request.values.get("password"),
        }
    account = data.get("account")
    password = sha1(data.get("passowrd", "").encode()).hexdigest()

    # 產生空白回覆
    response = make_response()
    response.headers["Content-type"] = "application/json"
    response.data = Json.dumps({"token": ""})

    # 驗證資料
    database = connect(**SQL_CONFIG)
    cursor = database.cursor()
    cursor.execute(f"SELECT discord_id FROM Users WHERE account=$1 AND password=$2;", (account, password))
    discord_id = cursor.fetchone()

    # 資料錯誤
    if discord_id == None:
        cursor.close()
        database.close()
        return response
    
    # 通過驗證，更新登入Token
    token = sha1(f"{datetime.now(TIMEZONE).isoformat()}{account}".encode()).hexdigest()
    cursor.execute(f"UPDATE Users SET token=$2 WHERE discord_id=$3;", (token, discord_id))
    database.commit()

    # 更新回覆
    response.data = Json.dumps({"token": token})
    response.set_cookie("token", token)

    cursor.close()
    database.close()
    return response

def run_thread() -> Thread:
    app.debug = WEB_DEBUG
    thread = Thread(target=wsgi.server, args=(eventlet.listen((WEB_HOST, WEB_PORT)), app, WEB_LOGGER), name="Dashboard")
    thread.start()
    return thread

if __name__ == "__main__":
    wsgi.server(eventlet.listen((WEB_HOST, WEB_PORT)), app, WEB_LOGGER)
