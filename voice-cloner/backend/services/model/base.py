from abc import ABC, abstractmethod
from pathlib import Path
import numpy as np


class VoiceModel(ABC):
    """Abstract base class for all TTS voice cloning engines."""

    # Subclasses must declare these
    ENGINE_NAME: str = ""
    LICENSE: str = ""
    COMMERCIAL_OK: bool = True
    SAMPLE_RATE: int = 44100

    @abstractmethod
    def load(self) -> None:
        """Load model weights into memory. Called once at startup."""
        ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        reference_wav: Path,
        speed: float = 1.0,
    ) -> np.ndarray:
        """
        Clone voice and synthesize text.

        Args:
            text: The text to speak (single chunk, max ~200 chars).
            reference_wav: Path to normalized 16kHz mono WAV reference audio.
            speed: Playback speed multiplier (0.7–1.3).

        Returns:
            Float32 numpy array at self.SAMPLE_RATE Hz (mono).
        """
        ...

    @property
    def is_loaded(self) -> bool:
        return getattr(self, "_loaded", False)
