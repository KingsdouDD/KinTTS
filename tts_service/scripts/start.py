"""
Start the qwe3 TTS service.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from service.lifecycle import LifecycleManager
import json

CONFIG_PATH = ROOT / "config" / "config.json"


def main():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    lm = LifecycleManager(config)

    if lm.is_running():
        pid = lm.get_pid()
        print(f"Service already running (PID={pid})")
        return

    print("Starting qwe3 TTS service...")
    ok = lm.start()
    if ok:
        print("Service started successfully")
    else:
        print("Failed to start service - check logs/qwe3-tts.log")


if __name__ == "__main__":
    main()
