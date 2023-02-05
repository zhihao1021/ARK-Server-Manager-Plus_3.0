from os import system
from os.path import isfile, getctime
from time import sleep

from psutil import AccessDenied, NoSuchProcess, Process

if __name__ == "__main__":
    last_change_time = 0
    while True:
        if isfile("PID"):
            if getctime("PID") != last_change_time:
                last_change_time = getctime("PID")
                with open("PID", mode="r") as pid_file:
                    last_pid = int(pid_file.read().strip())
                print(f"Running Process Change, PID: {last_pid}")
            try:
                print(f"Waiting For PID: {last_pid}")
                Process(last_pid).wait()
                print(f"PID - {last_pid} killed.")
                system("start cmd /c \"start.cmd\"")
            except (NoSuchProcess, AccessDenied):
                pass
        sleep(1)