"""
Model lifecycle manager for Qwen3-TTS.
All paths are computed dynamically from the file location.
Model is unloaded after each synthesis request by default, not kept resident.
"""

import json
import time
import gc
import os
import signal
from pathlib import Path
from threading import Thread, Lock
from mlx_audio.tts.utils import load_model

# All paths computed dynamically from this file's location
THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parent.parent
CONFIG_PATH = ROOT / "config" / "config.json"


def _load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


class ModelManager:
    def __init__(self, config_path: Path | None = None):
        cfg = _load_config() if config_path is None else json.load(open(config_path))
        model_path = cfg["model"]["id"]
        # Resolve relative paths from ROOT
        if not Path(model_path).is_absolute():
            model_path = str(ROOT / model_path)
        self.model_id = model_path
        self.idle_timeout = cfg["model"].get("idle_timeout", 600)
        self.lazy_load = cfg["model"].get("lazy_load", True)
        self.unload_after_request = cfg["model"].get("unload_after_request", True)

        self._model = None
        self._model_loaded = False
        self._last_used_at: float | None = None
        self._lock = Lock()
        self._idle_thread: Thread | None = None
        self._stop_idle_thread = False
        self._idle_exiting = False
        self._start_idle_thread()

    def _start_idle_thread(self):
        def check_loop():
            while not self._stop_idle_thread:
                time.sleep(30)
                self.check_idle_unload()
        t = Thread(target=check_loop, daemon=True)
        t.start()
        self._idle_thread = t

    def ensure_loaded(self):
        with self._lock:
            if self.is_loaded:
                self._last_used_at = time.time()
                return
            self._load_model()

    def _load_model(self):
        import logging
        logger = logging.getLogger("qwe3-tts")
        logger.info(f"Loading model: {self.model_id}")
        self._model = load_model(self.model_id, lazy=self.lazy_load)
        self._model_loaded = True
        self._last_used_at = time.time()
        logger.info("Model loaded successfully")

    def mark_used(self):
        self._last_used_at = time.time()

    def check_idle_unload(self):
        with self._lock:
            if self._idle_exiting:
                return
            if not self.is_loaded:
                return
            if self._last_used_at is None:
                return
            elapsed = time.time() - self._last_used_at
            if elapsed >= self.idle_timeout:
                self._unload_model()
                logger = __import__('logging').getLogger('qwe3-tts')
                logger.info(f"Idle timeout reached, model unloaded, process stays alive")

    def unload_after_synthesis(self):
        """Call this after each synthesis completes.
        Model stays loaded; only intermediate/session data is released.
        """
        if self.unload_after_request:
            with self._lock:
                self._unload_model()
        gc.collect()

    def _unload_model(self):
        import logging
        logger = logging.getLogger("qwe3-tts")
        if self._model is not None:
            logger.info("Unloading model from memory")
            del self._model
            self._model = None
            self._model_loaded = False
        else:
            self._model_loaded = False
        gc.collect()

    @property
    def is_loaded(self) -> bool:
        return self._model_loaded and self._model is not None

    def get_model(self):
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call ensure_loaded() first.")
        return self._model

    def status(self) -> dict:
        return {
            "model_id": self.model_id,
            "loaded": self.is_loaded,
            "last_used_at": self._last_used_at,
            "idle_seconds": int(time.time() - self._last_used_at) if self._last_used_at else 0,
        }
