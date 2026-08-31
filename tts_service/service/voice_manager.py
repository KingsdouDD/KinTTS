"""
Dynamic voice asset manager.
Scans voices/ directory, validates paths, prevents traversal attacks.
"""

import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
VOICES_DIR = ROOT / "voices"


class VoiceManager:
    def __init__(self):
        self._cache: dict[str, dict] = {}

    def list_voices(self) -> list[dict]:
        """Dynamically scan voices/ directory, return all valid voice assets."""
        voices = []
        if not VOICES_DIR.exists():
            return voices

        for voice_dir in VOICES_DIR.iterdir():
            if not voice_dir.is_dir():
                continue
            meta_path = voice_dir / "metadata.json"

            # Skip if missing metadata
            if not meta_path.exists():
                continue

            with open(meta_path) as f:
                meta = json.load(f)

            ref_audio_name = meta.get("reference_audio", "reference.wav")
            ref_path = voice_dir / ref_audio_name

            # Skip if reference audio file missing
            if not ref_path.exists():
                continue

            # Security: resolve and verify path stays within voices/
            resolved = voice_dir.resolve()
            if not str(resolved).startswith(str(VOICES_DIR.resolve())):
                continue

            voices.append({
                "id": voice_dir.name,
                "name": meta.get("name", voice_dir.name),
                "reference_audio": ref_path.name,
                "reference_path": str(ref_path),
                "reference_text": meta.get("reference_text", ""),
                "language": meta.get("language", "Chinese"),
                "description": meta.get("description", ""),
            })

        return voices

    def get_voice(self, voice_id: str) -> dict | None:
        voices = self.list_voices()
        for v in voices:
            if v["id"] == voice_id:
                return v
        return None

    def add_voice(
        self,
        voice_id: str,
        reference_audio_path: str,
        reference_text: str = "",
        language: str = "Chinese",
        description: str = "",
    ) -> dict:
        """Create a new voice asset from a reference audio file."""
        import logging
        logger = logging.getLogger("qwe3-tts")

        # Security: prevent path traversal
        safe_id = "".join(c for c in voice_id if c.isalnum() or c in "_-").lower()
        if not safe_id:
            raise ValueError("Invalid voice_id")

        voice_dir = VOICES_DIR / safe_id
        cache_dir = voice_dir / "cache"

        # Copy reference audio into the voice directory (not external reference)
        ref_src = Path(reference_audio_path).resolve()
        ref_dst = voice_dir / "reference.wav"
        ref_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ref_src, ref_dst)

        # Create metadata
        meta = {
            "id": safe_id,
            "name": safe_id,
            "reference_audio": "reference.wav",
            "reference_text": reference_text,
            "language": language,
            "description": description,
            "created_at": "",
            "updated_at": "",
        }
        with open(voice_dir / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        # Create empty cache dir
        cache_dir.mkdir(exist_ok=True)

        logger.info(f"Voice added: {safe_id}")
        return self.get_voice(safe_id)

    def remove_voice(self, voice_id: str) -> bool:
        """Remove a voice asset (only affects voices/, not models/)."""
        import logging
        logger = logging.getLogger("qwe3-tts")

        voice_dir = VOICES_DIR / voice_id
        if not voice_dir.exists():
            return False

        # Security: verify it stays within voices/
        resolved = voice_dir.resolve()
        if not str(resolved).startswith(str(VOICES_DIR.resolve())):
            return False

        shutil.rmtree(voice_dir)
        logger.info(f"Voice removed: {voice_id}")
        return True

    def resolve_voice_path(self, voice_id: str) -> Path | None:
        """Resolve voice directory path, with security check."""
        voice_dir = (VOICES_DIR / voice_id).resolve()
        if not str(voice_dir).startswith(str(VOICES_DIR.resolve())):
            return None
        meta_path = voice_dir / "metadata.json"
        if not meta_path.exists():
            return None
        with open(meta_path) as f:
            meta = json.load(f)
        ref_audio_name = meta.get("reference_audio", "reference.wav")
        ref = voice_dir / ref_audio_name
        if ref.exists():
            return ref
        return None
