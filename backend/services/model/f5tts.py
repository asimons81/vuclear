"""
F5-TTS engine — CC-BY-NC-4.0 (NON-COMMERCIAL ONLY).

⚠️  WARNING: The HuggingFace model weights for F5-TTS are licensed under
    CC-BY-NC-4.0. This means you CANNOT use this engine in any commercial
    product, SaaS, or paid service without violating the license.

    Only use VOICE_ENGINE=f5_noncommercial for personal, research, or
    educational purposes.

Weights: CC-BY-NC-4.0 (https://huggingface.co/SWivid/F5-TTS)
Code:    MIT
Install: pip install f5-tts
"""
import logging
from pathlib import Path

import numpy as np

from .base import VoiceModel

logger = logging.getLogger(__name__)

NC_WARNING = (
    "\n"
    "╔══════════════════════════════════════════════════════════════╗\n"
    "║  ⚠️  F5-TTS LICENSE WARNING                                   ║\n"
    "║                                                              ║\n"
    "║  F5-TTS model weights are CC-BY-NC-4.0 (non-commercial).    ║\n"
    "║  Do NOT use this engine in any commercial product or         ║\n"
    "║  paid service. For commercial use, switch to:                ║\n"
    "║    VOICE_ENGINE=chatterbox  (MIT)                            ║\n"
    "║    VOICE_ENGINE=metavoice   (Apache 2.0)                     ║\n"
    "╚══════════════════════════════════════════════════════════════╝\n"
)


class F5TTSModel(VoiceModel):
    ENGINE_NAME = "f5_noncommercial"
    LICENSE = "CC-BY-NC-4.0"
    COMMERCIAL_OK = False
    SAMPLE_RATE = 24000

    def __init__(self) -> None:
        self._model = None
        self._loaded = False

    def load(self) -> None:
        logger.warning(NC_WARNING)
        try:
            from f5_tts.api import F5TTS

            logger.info("Loading F5-TTS (CC-BY-NC-4.0 — non-commercial only)...")
            self._model = F5TTS()
            self._loaded = True
            logger.info("F5-TTS loaded (non-commercial use only)")
        except ImportError:
            raise RuntimeError(
                "F5-TTS is not installed. Run:\n"
                "  pip install f5-tts\n"
                "NOTE: CC-BY-NC-4.0 license — non-commercial use only."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load F5-TTS: {e}") from e

    def synthesize(
        self,
        text: str,
        reference_wav: Path,
        speed: float = 1.0,
    ) -> np.ndarray:
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        logger.debug("F5-TTS synthesize: %d chars, speed=%.2f", len(text), speed)

        wav, sr, _ = self._model.infer(
            ref_file=str(reference_wav),
            ref_text="",  # auto-transcribe reference
            gen_text=text,
            speed=speed,
        )

        audio = np.array(wav, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio.mean(axis=0)

        return audio
