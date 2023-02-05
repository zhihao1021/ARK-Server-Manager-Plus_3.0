from os import system
from os.path import isfile, getmtime
from time import sleep, time

from psutil import AccessDenied, NoSuchProcess, Process

if __name__ == "__main__":
    last_change_time = 0
    while True:
        if isfile("PID"):
            if getmtime("PID") != last_change_time:
                last_change_time = getmtime("PID")
                with open("PID", mode="r") as pid_file:
                    last_pid = int(pid_file.read().strip())
                print(f"{format(time(), '.2f')} Running Process Change, PID: {last_pid}")
            try:
                print(f"{format(time(), '.2f')} Waiting For PID: {last_pid}", end="\r")
                Process(last_pid).wait()
                print(f"\n{format(time(), '.2f')} PID - {last_pid} killed.")
                system("start cmd /c \"start.cmd\"")
            except (NoSuchProcess, AccessDenied):
                pass
        sleep(1)