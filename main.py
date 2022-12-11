from config import *
import logging_config
from dashboard import run_thread

thr = run_thread()
thr.join()

# thr.stop()
