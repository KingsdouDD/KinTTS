"""
TTS inference engine using official mlx-audio API.
Each segment: generate_audio(join_audio=True) → copy output to final location.
One model instance, multiple voices, no concurrency.
"""

import uuid
import shutil
import gc
import logging
from pathlib import Path

from .model_manager import ModelManager
from .voice_manager import VoiceManager
from .text_splitter import split_text
from .audio_processor import concatenate_wavs

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_TMP = ROOT / "runtime" / "tmp"
OUTPUTS = ROOT / "outputs"

logger = logging.getLogger("qwe3-tts")


class InferenceEngine:
    def __init__(self, model_manager: ModelManager, voice_manager: VoiceManager, config: dict):
        self.mm = model_manager
        self.vm = voice_manager
        self.cfg = config
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str = "Chinese",
    ) -> dict:
        if self._busy:
            return {"success": False, "error": "TTS service is busy"}
        self._busy = True
        try:
            return self._synthesize_impl(text, voice_id, language)
        finally:
            self._busy = False

    def _synthesize_impl(self, text: str, voice_id: str, language: str) -> dict:
        request_id = str(uuid.uuid4())[:8]

        # Validate voice and get full metadata
        voice_info = self.vm.get_voice(voice_id)
        if voice_info is None:
            return {"success": False, "error": f"Voice '{voice_id}' not found"}
        ref_audio = voice_info["reference_path"]
        ref_text = voice_info.get("reference_text", "")

        # Ensure model loaded
        self.mm.ensure_loaded()
        model = self.mm.get_model()
        self.mm.mark_used()

        # Split text
        max_chars = self.cfg["tts"]["max_segment_chars"]
        segments = split_text(text, max_chars)
        if not segments:
            return {"success": False, "error": "No text to synthesize"}

        logger.info(f"Request {request_id}: voice={voice_id}, segments={len(segments)}")

        # Official API: generate_audio with join_audio=True per segment
        from mlx_audio.tts.generate import generate_audio

        tmp_dir = RUNTIME_TMP / request_id
        tmp_dir.mkdir(parents=True, exist_ok=True)

        segment_files = []
        try:
            for i, seg in enumerate(segments):
                logger.info(f"  segment {i+1}/{len(segments)} generating...")
                # output_path must be a directory; official API writes {output_path}/audio.wav
                seg_out_dir = tmp_dir / f"seg_{i:03d}"
                seg_out_dir.mkdir(parents=True, exist_ok=True)

                generate_audio(
                    text=seg,
                    model=model,
                    ref_audio=str(ref_audio),
                    ref_text=ref_text,
                    lang_code=self.cfg["tts"]["lang_code"],
                    stream=False,
                    join_audio=True,
                    output_path=str(seg_out_dir),
                    save=True,
                    use_zero_spk_emb=False,
                    verbose=False,
                )

                # Official API writes to {output_path}/audio.wav
                generated_wav = seg_out_dir / "audio.wav"
                if not generated_wav.exists():
                    raise FileNotFoundError(f"Expected {generated_wav} not found")

                segment_files.append(str(generated_wav))
                logger.info(f"  segment {i+1}/{len(segments)} done")

        except Exception as e:
            logger.error(f"Generation error: {e}")
            import traceback
            traceback.print_exc()
            shutil.rmtree(tmp_dir, ignore_errors=True)
            gc.collect()
            return {
                "success": False,
                "request_id": request_id,
                "error": str(e),
            }

        # Concatenate all segment WAVs into one final file
        output_wav = OUTPUTS / f"{request_id}.wav"
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        try:
            concatenate_wavs(segment_files, output_wav)
        except Exception as e:
            logger.error(f"Concatenation error: {e}")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return {
                "success": False,
                "request_id": request_id,
                "error": f"Concatenation failed: {e}",
            }

        # Clean up tmp
        shutil.rmtree(tmp_dir, ignore_errors=True)

        # Duration
        import wave
        try:
            with wave.open(str(output_wav), "rb") as w:
                duration = w.getnframes() / w.getframerate()
        except Exception:
            duration = 0.0

        logger.info(f"Request {request_id}: done, output={output_wav}, duration={duration:.1f}s")

        # Release model after synthesis (keeps memory from growing)
        self.mm.unload_after_synthesis()
        gc.collect()

        return {
            "success": True,
            "request_id": request_id,
            "voice": voice_id,
            "output": str(output_wav),
            "duration": round(duration, 1),
            "segments": len(segments),
        }
