"""Unit tests for audio pipeline utilities."""
import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from backend.services.audio_pipeline import (
    CHUNK_MAX_CHARS,
    split_script,
)


class TestSplitScript:
    def test_empty_string_returns_empty(self):
        assert split_script("") == []

    def test_single_short_sentence(self):
        chunks = split_script("Hello world.")
        assert chunks == ["Hello world."]

    def test_multiple_sentences_fit_in_one_chunk(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = split_script(text, chunk_size=200)
        assert len(chunks) == 1
        assert "First sentence." in chunks[0]

    def test_long_text_splits_correctly(self):
        # Create text that definitely needs splitting
        sentence = "A" * 180 + "."
        text = f"{sentence} {sentence}"
        chunks = split_script(text, chunk_size=CHUNK_MAX_CHARS)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c) <= CHUNK_MAX_CHARS + 50  # small buffer for word boundaries

    def test_no_empty_chunks(self):
        text = "  Hello.   World.   Goodbye.  "
        chunks = split_script(text)
        assert all(c.strip() for c in chunks)

    def test_strips_whitespace(self):
        text = "\n\nHello world.\n\n"
        chunks = split_script(text)
        assert chunks[0] == "Hello world."

    def test_very_long_single_sentence_splits_by_word(self):
        # A sentence longer than CHUNK_MAX_CHARS with no punctuation
        words = ["word"] * 60
        text = " ".join(words)  # ~300 chars
        chunks = split_script(text, chunk_size=100)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c) <= 110  # allows small overflow for a single long word


class TestPreprocessReference:
    """Integration-ish tests that require ffmpeg."""

    @pytest.fixture
    def sample_wav(self, tmp_path: Path) -> Path:
        """Create a synthetic 10-second 16kHz mono WAV for testing."""
        sr = 16000
        duration = 10
        t = np.linspace(0, duration, sr * duration)
        # Generate 440Hz tone
        audio = 0.3 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
        path = tmp_path / "sample.wav"
        sf.write(str(path), audio, sr, subtype="PCM_16")
        return path

    def test_preprocess_returns_duration(self, sample_wav: Path, tmp_path: Path):
        pytest.importorskip("subprocess")
        from backend.services.audio_pipeline import preprocess_reference
        out = tmp_path / "reference.wav"
        try:
            duration = preprocess_reference(sample_wav, out)
            assert duration > 0
            assert out.exists()
        except RuntimeError as e:
            if "ffmpeg" in str(e).lower():
                pytest.skip("ffmpeg not available")
            raise


class TestValidateAudioFile:
    def test_rejects_non_audio(self, tmp_path: Path):
        from backend.services.audio_pipeline import validate_audio_file
        f = tmp_path / "fake.wav"
        f.write_text("not audio content")
        with pytest.raises((ValueError, Exception)):
            validate_audio_file(f)
