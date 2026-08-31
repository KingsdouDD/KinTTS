"""
Download Qwen3-TTS model if not already present.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "Qwen3-TTS-12Hz-1.7B-Base"
MODEL_ID = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-4bit"


def main():
    if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
        print(f"Model already exists at {MODEL_DIR}")
        return

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL_ID} ...")

    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False,
    )
    print(f"Model downloaded to {MODEL_DIR}")


if __name__ == "__main__":
    main()
