#!/usr/bin/env python3
"""
强制清理 qwe3-tts 服务进程，确保端口完全释放。
"""
import os
import signal
import subprocess
import time

PORT = 18170

def main():
    # 找到占用端口的进程
    result = subprocess.run(
        ["lsof", "-i", f":{PORT}", "-t"],
        capture_output=True, text=True
    )
    pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
    
    if not pids:
        print("No process on port", PORT)
        return
    
    for pid in pids:
        print(f"Killing PID {pid}...")
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError as e:
            print(f"  Failed to kill {pid}: {e}")
    
    # 等待端口完全释放
    for _ in range(10):
        result = subprocess.run(
            ["lsof", "-i", f":{PORT}", "-t"],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            print("Port clear.")
            return
        time.sleep(0.5)
    
    print("WARNING: Port may still be in use")

if __name__ == "__main__":
    main()
