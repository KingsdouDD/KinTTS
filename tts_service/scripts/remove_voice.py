"""
Remove a voice from qwe3 TTS.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from service.voice_manager import VoiceManager


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/remove_voice.py <voice_id>")
        sys.exit(1)

    voice_id = sys.argv[1]
    vm = VoiceManager()
    ok = vm.remove_voice(voice_id)
    print(f"Voice removed: {ok}")


if __name__ == "__main__":
    main()
