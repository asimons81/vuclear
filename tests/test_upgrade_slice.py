"""Tests for the first Vuclear upgrade slice: effects + job lifecycle helpers."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest

from backend.services import audio_pipeline, job_service
from backend.services.effects import apply_effects


class TestEffectsPipeline:
    def test_dry_preset_returns_same_audio(self):
        audio = np.array([0.1, -0.2, 0.3], dtype=np.float32)

        result = apply_effects(audio, sample_rate=44100, preset="dry")

        assert np.allclose(result, audio)
        assert result.dtype == np.float32

    def test_telephone_preset_changes_audio_but_keeps_shape(self):
        audio = np.sin(np.linspace(0, 8 * np.pi, 1024)).astype(np.float32) * 0.25

        result = apply_effects(audio, sample_rate=44100, preset="telephone")

        assert result.shape == audio.shape
        assert result.dtype == np.float32
        assert not np.allclose(result, audio)
        assert np.max(np.abs(result)) <= 1.0


class TestRunSynthesisPipeline:
    def test_applies_requested_effects_preset(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        calls: list[str | None] = []

        class FakeModel:
            SAMPLE_RATE = 16000

            def synthesize(self, text: str, reference_wav: Path, speed: float = 1.0):
                assert text == "Hello world."
                assert reference_wav == tmp_path / "reference.wav"
                assert speed == 1.0
                return np.ones(20000, dtype=np.float32) * 0.15

        def fake_get_model():
            return FakeModel()

        def fake_apply_effects(audio: np.ndarray, sample_rate: int, preset: str | None = None):
            calls.append(preset)
            return audio * 0.5

        def fake_run(cmd: list[str], capture_output: bool, text: bool):
            if cmd[0] == "ffmpeg":
                Path(cmd[-1]).write_bytes(b"mp3")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            raise AssertionError(f"Unexpected command: {cmd}")

        monkeypatch.setattr("backend.services.model.factory.get_model", fake_get_model)
        monkeypatch.setattr(audio_pipeline, "apply_effects", fake_apply_effects)
        monkeypatch.setattr(audio_pipeline.subprocess, "run", fake_run)

        reference_wav = tmp_path / "reference.wav"
        reference_wav.write_bytes(b"ref")
        output_dir = tmp_path / "output"

        wav_path, mp3_path, duration = audio_pipeline.run_synthesis_pipeline(
            reference_wav=reference_wav,
            script="Hello world.",
            output_dir=output_dir,
            speed=1.0,
            pause_ms=0,
            effects_preset="telephone",
        )

        assert calls == ["telephone"]
        assert wav_path.exists()
        assert mp3_path.exists()
        assert duration > 0


class TestLongFormChunking:
    def test_split_script_handles_abbreviations_cjk_and_tags(self):
        text = "Dr. Smith said hello. 他看见了。然后离开了！ [pause] Then he left."

        chunks = audio_pipeline.split_script(text, chunk_size=25)

        assert chunks == [
            "Dr. Smith said hello.",
            "他看见了。",
            "然后离开了！",
            "[pause] Then he left.",
        ]

    def test_crossfade_join_reduces_boundary_silence(self):
        from backend.services.audio_pipeline import join_audio_chunks_with_crossfade

        first = np.ones(44100, dtype=np.float32) * 0.25
        second = np.ones(44100, dtype=np.float32) * 0.5

        combined = join_audio_chunks_with_crossfade([first, second], sample_rate=44100, crossfade_ms=100)

        assert combined.shape[0] == 44100 + 44100 - 4410
        assert combined.dtype == np.float32
        assert np.max(np.abs(combined)) <= 1.0


class TestJobLifecycleHelpers:
    def test_create_retry_job_clones_original_job(self):
        original = job_service.create_job(
            voice_id="voice-1",
            script="Script text.",
            speed=1.1,
            pause_ms=250,
            effects_preset="broadcast",
        )
        updated = job_service.update_job(original["job_id"], status="failed", error="boom")

        retry = job_service.create_retry_job(updated["job_id"])

        assert retry["retry_of"] == original["job_id"]
        assert retry["attempt"] == 2
        assert retry["status"] == "queued"
        assert retry["voice_id"] == original["voice_id"]
        assert retry["script"] == original["script"]
        assert retry["effects_preset"] == "broadcast"

    def test_cancel_job_marks_queued_job_cancelled(self):
        job = job_service.create_job(
            voice_id="voice-2",
            script="Another script.",
            speed=1.0,
            pause_ms=300,
        )

        cancelled = job_service.cancel_job(job["job_id"])

        assert cancelled["status"] == "cancelled"
        assert cancelled["job_id"] == job["job_id"]

    def test_wait_for_job_returns_completed_job(self):
        job = job_service.create_job(
            voice_id="voice-3",
            script="Waiting script.",
            speed=1.0,
            pause_ms=300,
        )
        job_service.update_job(job["job_id"], status="completed", output_id="out-1")

        final_job = job_service.wait_for_job(job["job_id"], timeout_s=0.1)

        assert final_job["status"] == "completed"
        assert final_job["output_id"] == "out-1"
