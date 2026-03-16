#!/usr/bin/env python3
"""后台服务管理"""
import subprocess
import os
import sys
import signal
import time

def start():
    os.chdir('/root/.openclaw/workspace/secondlife/backend')
    with open('/tmp/sl.log', 'w') as f:
        proc = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
    with open('/tmp/sl.pid', 'w') as f:
        f.write(str(proc.pid))
    print(f"服务已启动 PID:{proc.pid}")
    return proc.pid

def stop():
    try:
        with open('/tmp/sl.pid') as f:
            pid = int(f.read())
        os.kill(pid, signal.SIGTERM)
        print(f"服务已停止 PID:{pid}")
    except:
        print("服务未运行")

def status():
    try:
        with open('/tmp/sl.pid') as f:
            pid = int(f.read())
        os.kill(pid, 0)
        print(f"✅ 服务运行中 PID:{pid}")
    except:
        print("❌ 服务未运行")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd == "start":
        stop()
        time.sleep(1)
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
