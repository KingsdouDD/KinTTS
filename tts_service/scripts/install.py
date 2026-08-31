"""
Installation script for qwe3 TTS.
Run: python scripts/install.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args, **kwargs):
    print(f"  $ {' '.join(args)}")
    r = subprocess.run(args, **kwargs)
    if r.returncode != 0:
        print(f"  FAILED (exit {r.returncode})")
        sys.exit(1)
    print("  OK")


def check(label, condition):
    status = "✅" if condition else "❌"
    print(f"{status} {label}")
    if not condition:
        sys.exit(1)


def main():
    print("=== qwe3 TTS Installation ===\n")

    # Check macOS
    import platform
    check("macOS", platform.system() == "Darwin")

    # Check Apple Silicon
    import subprocess
    cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.decode().strip()
    check(f"Apple Silicon ({cpu})", "Apple" in cpu or cpu.startswith("M"))

    # Check Python
    py_version = sys.version_info
    check(f"Python 3.10+ (current: {py_version.major}.{py_version.minor})", py_version >= (3, 10))

    # Check/create venv
    venv_dir = ROOT / ".venv"
    if not venv_dir.exists():
        print(f"\n📦 Creating virtual environment...")
        run(sys.executable, "-m", "venv", str(venv_dir))

    pip = venv_dir / "bin" / "pip"
    python = venv_dir / "bin" / "python"

    print(f"\n📦 Installing Python dependencies...")
    run(str(pip), "install", "--upgrade", "pip")
    run(str(pip), "install", "mlx-audio", "huggingface-hub")

    # Check FFmpeg
    import shutil
    check("FFmpeg", shutil.which("ffmpeg") is not None)

    # Create directories
    print("\n📁 Creating directory structure...")
    for d in ["voices", "outputs", "runtime/tmp", "logs"]:
        p = ROOT / d
        p.mkdir(exist_ok=True)
        print(f"  ✅ {d}")

    # Check model
    print("\n🤖 Checking model...")
    model_dir = ROOT / "models" / "Qwen3-TTS-12Hz-1.7B-Base"
    if model_dir.exists():
        print(f"  ✅ Model already exists at {model_dir}")
    else:
        print(f"  ⏳ Model not yet downloaded (will download on first use)")

    print("\n✅ Installation complete!")
    print(f"\nNext steps:")
    print(f"  1. python scripts/add_voice.py   # register a voice")
    print(f"  2. python scripts/start.py        # start the service")
    print(f"  3. python scripts/test.py         # run a test")


if __name__ == "__main__":
    main()
