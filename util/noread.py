import time
import signal
import sys

flag = False

def handler(signum, frame):
    global flag
    flag = not flag

signal.signal(signal.SIGUSR1, handler)

while True:
    if flag:
        sys.stdin.buffer.read(1024)
    else:
        time.sleep(0.1)
