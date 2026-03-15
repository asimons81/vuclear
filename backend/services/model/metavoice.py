"""
MetaVoice-1B engine — Apache 2.0, commercial use allowed.

Weights: Apache 2.0 (https://github.com/metavoiceio/metavoice-src)
Install: pip install metavoice
Hardware: Requires 10–12GB VRAM (RTX 3080+)

Use VOICE_ENGINE=metavoice to activate.
"""
import logging
from pathlib import Path

import numpy as np

from .base import VoiceModel

logger = logging.getLogger(__name__)


class MetaVoiceModel(VoiceModel):
    ENGINE_NAME = "metavoice"
    LICENSE = "Apache 2.0"
    COMMERCIAL_OK = True
    SAMPLE_RATE = 24000

    def __init__(self) -> None:
        self._model = None
        self._loaded = False

    def load(self) -> None:
        try:
            from fam.llm.fast_inference import TTS

            logger.info("Loading MetaVoice-1B (Apache 2.0 license)...")
            self._model = TTS()
            self._loaded = True
            logger.info("MetaVoice-1B loaded successfully")
        except ImportError:
            raise RuntimeError(
                "MetaVoice is not installed. Run:\n"
                "  pip install git+https://github.com/metavoiceio/metavoice-src.git"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load MetaVoice: {e}") from e

    def synthesize(
        self,
        text: str,
        reference_wav: Path,
        speed: float = 1.0,
    ) -> np.ndarray:
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        logger.debug("MetaVoice synthesize: %d chars", len(text))

        output_path = reference_wav.parent / "_metavoice_tmp.wav"
        self._model.synthesise(
            text=text,
            spk_ref_path=str(reference_wav),
            top_p=0.95,
            guidance_scale=3.0,
            output_path=str(output_path),
        )

        import soundfile as sf
        audio, _ = sf.read(str(output_path), dtype="float32")

        if abs(speed - 1.0) > 0.01:
            import librosa
            target_sr = int(self.SAMPLE_RATE / speed)
            audio = librosa.resample(audio, orig_sr=self.SAMPLE_RATE, target_sr=target_sr)

        return audio
