"""
Chatterbox TTS engine — MIT License, commercial use allowed.

Weights: MIT (https://github.com/resemble-ai/chatterbox)
Install: pip install chatterbox-tts
         OR: pip install git+https://github.com/resemble-ai/chatterbox.git

Chatterbox includes a built-in Perth perceptual watermark on all outputs.
This is a content authenticity feature — note it in any commercial deployment.
"""
import logging
from pathlib import Path

import numpy as np

from .base import VoiceModel

logger = logging.getLogger(__name__)


class ChatterboxModel(VoiceModel):
    ENGINE_NAME = "chatterbox"
    LICENSE = "MIT"
    COMMERCIAL_OK = True
    SAMPLE_RATE = 24000  # Chatterbox native output rate; we upsample in pipeline

    def __init__(self) -> None:
        self._model = None
        self._loaded = False
        self._device = "cpu"

    def load(self) -> None:
        try:
            import torch
            from chatterbox.tts import ChatterboxTTS

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Loading Chatterbox on device=%s", self._device)
            self._model = ChatterboxTTS.from_pretrained(device=self._device)
            self._loaded = True
            logger.info("Chatterbox loaded successfully (MIT license)")
        except ImportError:
            raise RuntimeError(
                "Chatterbox is not installed. Run:\n"
                "  pip install chatterbox-tts\n"
                "or: pip install git+https://github.com/resemble-ai/chatterbox.git"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load Chatterbox: {e}") from e

    def synthesize(
        self,
        text: str,
        reference_wav: Path,
        speed: float = 1.0,
    ) -> np.ndarray:
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        import torch

        logger.debug("Chatterbox synthesize: %d chars, speed=%.2f", len(text), speed)

        with torch.inference_mode():
            wav_tensor = self._model.generate(
                text=text,
                audio_prompt_path=str(reference_wav),
                # Chatterbox uses cfg_weight for style control; speed via post-process
            )

        # wav_tensor shape: (1, samples) or (samples,)
        audio = wav_tensor.squeeze().cpu().numpy().astype(np.float32)

        # Apply speed by resampling ratio if not 1.0
        if abs(speed - 1.0) > 0.01:
            import librosa
            target_sr = int(self.SAMPLE_RATE / speed)
            audio = librosa.resample(audio, orig_sr=self.SAMPLE_RATE, target_sr=target_sr)

        return audio
