"""Unit tests for audio pipeline utilities."""
import sys
import tempfile
import subprocess
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
        chunks = split_script(text, chunk_size=200)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c) <= 250  # small buffer for word boundaries

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

    def test_accepts_webm_magic_type(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        from backend.services import audio_pipeline

        f = tmp_path / "sample.webm"
        f.write_bytes(b"webm")

        class FakeMagic:
            @staticmethod
            def from_file(path: str, mime: bool = True) -> str:
                assert mime is True
                return "video/webm"

        monkeypatch.setitem(sys.modules, "magic", FakeMagic)
        monkeypatch.setattr(audio_pipeline, "get_audio_duration", lambda path: 6.0)

        mime, duration = audio_pipeline.validate_audio_file(f)
        assert mime == "video/webm"
        assert duration == 6.0


class TestGetAudioDuration:
    def test_uses_stream_duration_first(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        from backend.services.audio_pipeline import get_audio_duration

        audio_path = tmp_path / "sample.webm"
        audio_path.write_bytes(b"webm")

        def fake_run(cmd: list[str], capture_output: bool, text: bool):
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout='{"streams":[{"codec_type":"audio","duration":"5.5"}],"format":{}}',
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert get_audio_duration(audio_path) == pytest.approx(5.5)

    def test_uses_format_duration_fallback(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        from backend.services.audio_pipeline import get_audio_duration

        audio_path = tmp_path / "sample.webm"
        audio_path.write_bytes(b"webm")

        def fake_run(cmd: list[str], capture_output: bool, text: bool):
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout='{"streams":[{"codec_type":"audio"}],"format":{"duration":"6.125"}}',
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert get_audio_duration(audio_path) == pytest.approx(6.125)

    def test_uses_stream_tag_duration_fallback(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        from backend.services.audio_pipeline import get_audio_duration

        audio_path = tmp_path / "sample.webm"
        audio_path.write_bytes(b"webm")

        def fake_run(cmd: list[str], capture_output: bool, text: bool):
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout='{"streams":[{"codec_type":"audio","tags":{"DURATION":"00:00:06.500"}}],"format":{}}',
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)

        assert get_audio_duration(audio_path) == pytest.approx(6.5)

    def test_uses_decoded_pcm_fallback_when_metadata_missing(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        from backend.services import audio_pipeline

        audio_path = tmp_path / "sample.webm"
        audio_path.write_bytes(b"webm")

        def fake_run(cmd: list[str], capture_output: bool, text: bool):
            if cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout='{"streams":[{"codec_type":"audio"}],"format":{}}',
                    stderr="",
                )
            if cmd[0] == "ffmpeg":
                Path(cmd[-1]).write_bytes(b"decoded")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            raise AssertionError(f"Unexpected command: {cmd}")

        class FakeInfo:
            samplerate = 16000
            frames = 96000

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(audio_pipeline.sf, "info", lambda path: FakeInfo())

        assert audio_pipeline.get_audio_duration(audio_path) == pytest.approx(6.0)
