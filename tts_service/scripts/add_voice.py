"""
Add a new voice to qwe3 TTS.
Usage: python scripts/add_voice.py <voice_id> <reference_audio> [--text "参考文本"] [language]

如果不传 --text，则 reference_text 为空。
"""
import sys
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def convert_to_wav(src_path: Path, dst_path: Path):
    """Convert any audio to 24kHz mono float32 WAV using FFmpeg (对齐官方 mlx-audio 路径)."""
    cmd = [
        "ffmpeg", "-y", "-i", str(src_path),
        "-ar", "24000", "-ac", "1", "-acodec", "pcm_f32le",
        str(dst_path)
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed: {result.stderr.decode()}")


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python scripts/add_voice.py <voice_id> <reference_audio> [--text 'ref text'] [language]")
        sys.exit(1)

    voice_id = args[0]
    ref_audio = args[1]
    language = "Chinese"
    ref_text = ""

    # Parse optional --text (must come as a pair)
    i = 2
    while i < len(args):
        if args[i] == "--text" and i + 1 < len(args):
            ref_text = args[i + 1]
            i += 2
        else:
            # Remaining positional arg is language
            language = args[i]
            i += 1

    ref_path = Path(ref_audio).resolve()
    if not ref_path.exists():
        print(f"Reference audio not found: {ref_audio}")
        sys.exit(1)

    safe_id = "".join(c for c in voice_id if c.isalnum() or c in "_-").lower()
    voice_dir = ROOT / "voices" / safe_id
    ref_wav = voice_dir / "reference.wav"

    voice_dir.mkdir(parents=True, exist_ok=True)
    (voice_dir / "cache").mkdir(exist_ok=True)

    print(f"Converting {ref_path} to float32 WAV...")
    convert_to_wav(ref_path, ref_wav)

    if ref_text:
        print(f"Using reference text: {ref_text[:30]}...")
    else:
        print("No --text provided, reference_text left empty (合成时用零 speaker embedding)")

    meta = {
        "id": safe_id,
        "name": safe_id,
        "reference_audio": "reference.wav",
        "reference_text": ref_text,
        "language": language,
        "description": "",
        "created_at": "",
        "updated_at": "",
    }
    with open(voice_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Voice added: {safe_id}")


if __name__ == "__main__":
    main()
