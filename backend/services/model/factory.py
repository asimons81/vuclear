"""Model factory — selects VoiceModel implementation based on VOICE_ENGINE env."""
import logging
from functools import lru_cache

from .base import VoiceModel

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_model() -> VoiceModel:
    """
    Instantiate and load the configured voice model.
    Cached — only loads once per process.
    """
    from backend.config import settings

    engine = settings.voice_engine
    logger.info("Initializing voice engine: %s", engine)

    if engine == "chatterbox":
        from .chatterbox import ChatterboxModel
        model = ChatterboxModel()
    elif engine == "metavoice":
        from .metavoice import MetaVoiceModel
        model = MetaVoiceModel()
    elif engine == "f5_noncommercial":
        from .f5tts import F5TTSModel
        model = F5TTSModel()
    else:
        raise ValueError(f"Unknown VOICE_ENGINE: {engine!r}")

    model.load()
    logger.info(
        "Engine loaded: %s | License: %s | Commercial: %s",
        model.ENGINE_NAME,
        model.LICENSE,
        "YES" if model.COMMERCIAL_OK else "NO — non-commercial only",
    )
    return model
