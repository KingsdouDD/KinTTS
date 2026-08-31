"""
OpenClaw tool registration for qwe3 TTS.
Import this file to register all qwe3_tts_* tools with OpenClaw.
"""

from openclaw import tools as openclaw_tools

from .tools import (
    qwe3_tts,
    qwe3_tts_list_voices,
    qwe3_tts_add_voice,
    qwe3_tts_remove_voice,
    qwe3_tts_health,
    qwe3_tts_start,
    qwe3_tts_unload,
    qwe3_tts_query_log,
)


def register():
    """Register all qwe3 TTS tools with OpenClaw."""
    openclaw_tools.add(
        name="qwe3_tts",
        description="Synthesize long text to speech using a cloned voice. Automatically splits long text into segments, generates each, and concatenates into one audio file.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The full text to synthesize (can be 800+ characters)"},
                "voice": {"type": "string", "description": "Voice ID from qwe3_tts_list_voices (e.g. speaker_001)"},
                "language": {"type": "string", "description": "Language hint", "default": "Chinese"},
            },
            "required": ["text", "voice"],
        },
        handler=qwe3_tts,
    )

    openclaw_tools.add(
        name="qwe3_tts_list_voices",
        description="List all available cloned voices in qwe3 TTS.",
        parameters={"type": "object", "properties": {}},
        handler=qwe3_tts_list_voices,
    )

    openclaw_tools.add(
        name="qwe3_tts_add_voice",
        description="Register a new voice clone from a reference audio file.",
        parameters={
            "type": "object",
            "properties": {
                "voice_id": {"type": "string", "description": "Unique ID for this voice (e.g. dileba_01)"},
                "reference_audio": {"type": "string", "description": "Path to reference audio file (3+ seconds of one speaker)"},
                "reference_text": {"type": "string", "description": "Transcript of the reference audio"},
                "language": {"type": "string", "description": "Language of the reference audio", "default": "Chinese"},
                "description": {"type": "string", "description": "Human-readable description"},
            },
            "required": ["voice_id", "reference_audio"],
        },
        handler=qwe3_tts_add_voice,
    )

    openclaw_tools.add(
        name="qwe3_tts_remove_voice",
        description="Remove a registered voice from qwe3 TTS.",
        parameters={
            "type": "object",
            "properties": {
                "voice_id": {"type": "string", "description": "Voice ID to remove"},
            },
            "required": ["voice_id"],
        },
        handler=qwe3_tts_remove_voice,
    )

    openclaw_tools.add(
        name="qwe3_tts_health",
        description="Check qwe3 TTS service health and model status.",
        parameters={"type": "object", "properties": {}},
        handler=qwe3_tts_health,
    )

    openclaw_tools.add(
        name="qwe3_tts_start",
        description="Start the qwe3 TTS background service.",
        parameters={"type": "object", "properties": {}},
        handler=qwe3_tts_start,
    )

    openclaw_tools.add(
        name="qwe3_tts_unload",
        description="Unload the TTS model from memory (frees RAM).",
        parameters={"type": "object", "properties": {}},
        handler=qwe3_tts_unload,
    )

    openclaw_tools.add(
        name="qwe3_tts_query_log",
        description="Query TTS synthesis logs and return detailed timing for each request: audio duration, start/end time, elapsed time, and speed multiplier.",
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of recent requests to return (default: 10)"},
            },
        },
        handler=qwe3_tts_query_log,
    )
