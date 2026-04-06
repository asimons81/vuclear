"""Tests for voice profile samples and generation versioning."""
from __future__ import annotations

import json
from pathlib import Path

from backend.config import settings
from backend.services import output_service, voice_service


def test_create_voice_profile_initializes_sample_list(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    profile = voice_service.create_voice_profile(
        name="Tony",
        consent=True,
        duration_s=12.3,
        ip_hash="abc123",
        engine="chatterbox",
    )

    assert profile["sample_count"] == 1
    assert len(profile["samples"]) == 1
    assert profile["samples"][0]["duration_s"] == 12.3

    stored = json.loads((tmp_path / "voices" / profile["voice_id"] / "profile.json").read_text())
    assert stored["sample_count"] == 1
    assert stored["samples"][0]["kind"] == "reference"


def test_add_voice_sample_appends_sample_and_updates_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    profile = voice_service.create_voice_profile(
        name="Tony",
        consent=True,
        duration_s=10.0,
        ip_hash="abc123",
        engine="chatterbox",
    )

    sample = voice_service.add_voice_sample(profile["voice_id"], duration_s=8.5, kind="training", note="second mic take")

    assert sample["kind"] == "training"
    assert sample["note"] == "second mic take"

    updated = voice_service.get_voice_profile(profile["voice_id"])
    assert updated["sample_count"] == 2
    assert updated["samples"][-1]["duration_s"] == 8.5
    assert updated["total_duration_s"] == 18.5


def test_create_output_records_generation_lineage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    meta = output_service.create_output(
        output_id="out-1",
        job_id="job-2",
        voice_id="voice-9",
        script="Hello there.",
        speed=1.0,
        pause_ms=300,
        duration_s=2.5,
        chunk_size=800,
        crossfade_ms=120,
        effects_preset="warm",
        generation_id="job-1",
        take_number=2,
        lineage_job_id="job-1",
    )

    assert meta["generation_id"] == "job-1"
    assert meta["take_number"] == 2
    assert meta["lineage_job_id"] == "job-1"

    grouped = output_service.list_output_takes("job-1")
    assert len(grouped) == 1
    assert grouped[0]["take_number"] == 2
