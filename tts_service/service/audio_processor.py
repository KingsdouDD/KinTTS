"""
Audio concatenation using Python wave module (no FFmpeg dependency).
"""

import wave
import numpy as np
from pathlib import Path


def concatenate_wavs(paths: list[str], out_path: Path):
    """
    Concatenate multiple WAV files into one using Python's wave module.
    All input WAVs must have the same sample rate and channels.
    """
    sample_rate = None
    nchannels = None
    sampwidth = None
    all_frames = []

    for p in paths:
        with wave.open(str(p), "rb") as w:
            if sample_rate is None:
                sample_rate = w.getframerate()
                nchannels = w.getnchannels()
                sampwidth = w.getsampwidth()
            else:
                # Verify compatibility
                if w.getframerate() != sample_rate:
                    raise ValueError(f"Incompatible sample rate: {w.getframerate()} vs {sample_rate}")
                if w.getnchannels() != nchannels:
                    raise ValueError(f"Incompatible channels: {w.getnchannels()} vs {nchannels}")
            frames = w.readframes(w.getnframes())
            all_frames.append(frames)

    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(sample_rate)
        for frames in all_frames:
            w.writeframes(frames)
