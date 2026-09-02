"""
OpenClaw tool wrappers for qwe3 TTS.
These are the tools registered with the OpenClaw agent.
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "config.json"


def _load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _api(path: str, method: str = "GET", data: dict | None = None) -> dict:
    cfg = _load_config()
    host = cfg["server"]["host"]
    port = cfg["server"]["port"]
    url = f"http://{host}:{port}{path}"

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        # Try to restart service if connection refused
        from service.lifecycle import LifecycleManager
        lm = LifecycleManager(cfg)
        if lm.is_running():
            raise
        lm.start()
        # Retry once
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())


def qwe3_tts(text: str, voice: str = "speaker_001", language: str = "Chinese") -> dict:
    """
    Synthesize long text to speech using a cloned voice.
    Automatically splits long text into segments, generates each, and concatenates into one audio file.

    Args:
        text: The full text to synthesize (can be 800+ characters)
        voice: Voice ID from qwe3_tts_list_voices (e.g. "speaker_001")
        language: Language hint (default: Chinese)
    """
    return _api("/tts", method="POST", data={
        "text": text,
        "voice": voice,
        "language": language,
    })


def qwe3_tts_list_voices() -> dict:
    """List all available cloned voices."""
    return _api("/voices")


def qwe3_tts_add_voice(
    voice_id: str,
    reference_audio: str,
    reference_text: str = "",
    language: str = "Chinese",
    description: str = "",
) -> dict:
    """
    Register a new voice clone from a reference audio file.

    Args:
        voice_id: Unique ID for this voice (e.g. "dileba_01")
        reference_audio: Path to reference audio file (3+ seconds of one speaker)
        reference_text: Transcript of the reference audio (optional)
        language: Language of the reference audio (default: Chinese)
        description: Human-readable description
    """
    return _api("/voices/register", method="POST", data={
        "voice_id": voice_id,
        "reference_audio": reference_audio,
        "reference_text": reference_text,
        "language": language,
        "description": description,
    })


def qwe3_tts_remove_voice(voice_id: str) -> dict:
    """Remove a registered voice."""
    return _api("/voices/remove", method="POST", data={"voice_id": voice_id})


def qwe3_tts_health() -> dict:
    """Check TTS service health and model status."""
    return _api("/health")


def qwe3_tts_start() -> dict:
    """Start the qwe3 TTS service."""
    from service.lifecycle import LifecycleManager
    cfg = _load_config()
    lm = LifecycleManager(cfg)
    ok = lm.start()
    return {"success": ok, "message": "Service started" if ok else "Failed to start"}


def qwe3_tts_unload() -> dict:
    """Unload the TTS model from memory."""
    return _api("/unload", method="POST")


def qwe3_tts_query_log(limit: int = 10) -> dict:
    """
    Query the TTS synthesis log and return detailed timing for each request.

    Args:
        limit: Number of recent requests to return (default: 10)

    Returns:
        {
          "logs": [
            {
              "id": "abc123",
              "voice": "you_voice",
              "segments": 41,
              "audio_duration": 217.2,
              "start_time": "16:48:16",
              "end_time": "16:50:15",
              "elapsed_seconds": 119,
              "speed": 1.83
            },
            ...
          ]
        }
    """
    import re
    from datetime import datetime

    log_path = ROOT / "logs" / "qwe3-tts.log"
    if not log_path.exists():
        return {"error": "log file not found", "path": str(log_path)}

    content = log_path.read_text(encoding="utf-8")

    # 解析开始行: Request <id>: voice=<voice>, segments=<n>
    # 解析结束行: Request <id>: done, output=..., duration=<n>s
    start_pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2}),\d+)"  # timestamp
        r"\s+\[INFO\].*?Request\s+([a-f0-9]+):"  # id
        r"\s+voice=([^,]+),"  # voice
        r"\s+segments=(\d+)"  # segments
    )
    end_pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2} (\d{2}:\d{2}:\d{2}),\d+)"  # timestamp
        r"\s+\[INFO\].*?Request\s+([a-f0-9]+):.*?"  # id
        r"duration=([\d.]+)s"  # audio_duration
    )

    starts = {}  # id -> {voice, segments, start_ts, start_time_str}
    for m in start_pattern.finditer(content):
        ts_str = m.group(1)
        rid = m.group(3)
        voice = m.group(4).strip()
        segments = int(m.group(5))
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        starts[rid] = {
            "id": rid,
            "voice": voice,
            "segments": segments,
            "start_dt": dt,
            "start_time": m.group(2),
        }

    results = []
    for m in end_pattern.finditer(content):
        rid = m.group(3)
        if rid not in starts:
            continue
        audio_duration = float(m.group(5))
        end_dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        start_dt = starts[rid]["start_dt"]
        elapsed = (end_dt - start_dt).total_seconds()
        speed = round(audio_duration / elapsed, 2) if elapsed > 0 else 0
        results.append({
            **starts[rid],
            "end_time": m.group(2),
            "audio_duration": audio_duration,
            "elapsed_seconds": round(elapsed, 1),
            "speed": speed,
        })

    results.sort(key=lambda x: x["start_dt"], reverse=True)
    results = results[:limit]
    for r in results:
        del r["start_dt"]

    return {"logs": results}
