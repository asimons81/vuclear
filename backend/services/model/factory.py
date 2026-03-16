"""Model factory — selects VoiceModel implementation based on VOICE_ENGINE env."""
import logging
import threading
from typing import Optional

from .base import VoiceModel

logger = logging.getLogger(__name__)

# ─── Singleton state ──────────────────────────────────────────────────────────
# Protected by _lock. Read without lock is safe for status checks (GIL + no
# partial-write risk on reference assignment), but we only *write* under lock.
_lock = threading.Lock()
_instance: Optional[VoiceModel] = None
_loading: bool = False
_load_error: Optional[str] = None


def get_model() -> VoiceModel:
    """
    Return the loaded voice model. Thread-safe singleton.

    Blocks the calling thread until the model is loaded.
    Raises RuntimeError (or ValueError) if loading fails.
    """
    global _instance, _loading, _load_error

    # Fast path — already loaded, no lock needed.
    if _instance is not None:
        return _instance

    with _lock:
        # Re-check inside lock — a concurrent thread may have finished loading
        # while we were waiting to acquire it.
        if _instance is not None:
            return _instance

        from backend.config import settings

        engine = settings.voice_engine
        logger.info("Initializing voice engine: %s", engine)

        _loading = True
        _load_error = None

        try:
            if engine == "chatterbox":
                from .chatterbox import ChatterboxModel
                model: VoiceModel = ChatterboxModel()
            elif engine == "metavoice":
                from .metavoice import MetaVoiceModel
                model = MetaVoiceModel()
            elif engine == "f5_noncommercial":
                from .f5tts import F5TTSModel
                model = F5TTSModel()
            else:
                raise ValueError(f"Unknown VOICE_ENGINE: {engine!r}")

            model.load()
            _instance = model
            logger.info(
                "Engine loaded: %s | License: %s | Commercial: %s",
                model.ENGINE_NAME,
                model.LICENSE,
                "YES" if model.COMMERCIAL_OK else "NO — non-commercial only",
            )
            return model

        except Exception as e:
            _load_error = str(e)
            logger.error("Voice engine load failed: %s", e)
            raise

        finally:
            _loading = False


def get_model_status() -> dict:
    """
    Non-blocking model status snapshot. Does NOT trigger loading.
    Safe to call from health endpoints and status routes.
    """
    return {
        "loaded": _instance is not None and _instance.is_loaded,
        "loading": _loading,
        "error": _load_error,
        "engine_name": _instance.ENGINE_NAME if _instance is not None else None,
        "commercial_ok": _instance.COMMERCIAL_OK if _instance is not None else None,
        "license": _instance.LICENSE if _instance is not None else None,
    }
