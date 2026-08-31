"""
Basic test script for qwe3 TTS.
"""

import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from service.model_manager import ModelManager
from service.voice_manager import VoiceManager
from service.inference import InferenceEngine
from service.lifecycle import LifecycleManager

CONFIG_PATH = ROOT / "config" / "config.json"


def get_rss():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB


def main():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    print("=== qwe3 TTS Test ===\n")

    # Start service
    lm = LifecycleManager(config)
    if not lm.is_running():
        print("Starting service...")
        lm.start()
        time.sleep(2)

    print(f"RSS (idle): {get_rss():.1f} MB")

    # Init engine components
    mm = ModelManager(CONFIG_PATH)
    vm = VoiceManager()
    engine = InferenceEngine(mm, vm, config)

    # List voices
    voices = vm.list_voices()
    print(f"\nVoices: {len(voices)}")
    for v in voices:
        print(f"  - {v['id']}: {v['name']}")

    if not voices:
        print("No voices found. Run: python scripts/add_voice.py first")
        return

    # Test TTS with a short text
    test_text = "你好，这是一个语音合成测试。今天天气不错，我们来测试一下文字转语音的功能。"

    print(f"\nTest text: {test_text}")
    print(f"RSS before TTS: {get_rss():.1f} MB")

    result = engine.synthesize(test_text, voices[0]["id"])

    print(f"\nResult: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print(f"RSS after TTS: {get_rss():.1f} MB")


if __name__ == "__main__":
    main()
