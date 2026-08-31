"""
Stop the qwe3 TTS service.
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
    lm.stop()
    print("Service stopped")


if __name__ == "__main__":
    main()
