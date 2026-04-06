"""Voice profile CRUD and storage service."""
import hashlib
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _voice_dir(voice_id: str) -> Path:
    return settings.voices_dir / voice_id


def _profile_path(voice_id: str) -> Path:
    return _voice_dir(voice_id) / "profile.json"


def _reference_path(voice_id: str) -> Path:
    return _voice_dir(voice_id) / "reference.wav"


def _samples_dir(voice_id: str) -> Path:
    return _voice_dir(voice_id) / "samples"


def _sample_path(voice_id: str, sample_id: str, filename: str = "sample.wav") -> Path:
    return _samples_dir(voice_id) / sample_id / filename


def _normalize_profile(profile: dict) -> dict:
    samples = profile.get("samples") or []
    if not samples:
        samples = [
            {
                "sample_id": f"{profile['voice_id']}-reference",
                "kind": "reference",
                "duration_s": round(float(profile.get("duration_s", 0.0)), 2),
                "note": None,
                "filename": "reference.wav",
                "created_at": profile.get("created_at", _now_iso()),
            }
        ]

    profile.setdefault("samples", samples)
    profile["sample_count"] = len(samples)
    profile["total_duration_s"] = round(sum(float(sample.get("duration_s", 0.0)) for sample in samples), 2)
    return profile


def _save_profile(profile: dict) -> dict:
    normalized = _normalize_profile(profile)
    _voice_dir(normalized["voice_id"]).mkdir(parents=True, exist_ok=True)
    _profile_path(normalized["voice_id"]).write_text(json.dumps(normalized, indent=2))
    return normalized


def create_voice_profile(
    name: str,
    consent: bool,
    duration_s: float,
    ip_hash: str,
    engine: str,
    voice_id: str | None = None,
) -> dict:
    """Create and persist a voice profile. Returns profile dict."""
    if not consent:
        raise ValueError("Consent is required to create a voice profile")

    voice_id = voice_id or str(uuid.uuid4())
    profile = {
        "voice_id": voice_id,
        "name": name,
        "consent": True,
        "created_at": _now_iso(),
        "duration_s": round(duration_s, 2),
        "engine": engine,
        "ip_hash": ip_hash,
        "samples": [
            {
                "sample_id": f"{voice_id}-reference",
                "kind": "reference",
                "duration_s": round(duration_s, 2),
                "note": None,
                "filename": "reference.wav",
                "created_at": _now_iso(),
            }
        ],
    }

    _save_profile(profile)

    _write_audit(voice_id, "voice_created", ip_hash)
    logger.info("Voice profile created: %s (%s)", voice_id, name)
    return _normalize_profile(profile)


def get_voice_profile(voice_id: str) -> Optional[dict]:
    path = _profile_path(voice_id)
    if not path.exists():
        return None
    return _normalize_profile(json.loads(path.read_text()))


def list_voice_profiles() -> list[dict]:
    profiles = []
    for profile_path in settings.voices_dir.glob("*/profile.json"):
        try:
            profiles.append(_normalize_profile(json.loads(profile_path.read_text())))
        except Exception as e:
            logger.warning("Failed to read profile %s: %s", profile_path, e)
    profiles.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return profiles


def add_voice_sample(
    voice_id: str,
    duration_s: float,
    *,
    kind: str = "additional",
    note: str | None = None,
    source_path: Path | None = None,
) -> dict:
    profile = get_voice_profile(voice_id)
    if not profile:
        raise KeyError(f"Voice not found: {voice_id}")

    sample_id = str(uuid.uuid4())
    filename = source_path.name if source_path is not None else "sample.wav"
    sample_dir = _samples_dir(voice_id) / sample_id
    sample_dir.mkdir(parents=True, exist_ok=True)

    if source_path is not None:
        destination = sample_dir / filename
        shutil.copy2(source_path, destination)
        stored_filename = filename
    else:
        destination = sample_dir / filename
        stored_filename = filename

    sample = {
        "sample_id": sample_id,
        "kind": kind,
        "duration_s": round(duration_s, 2),
        "note": note,
        "filename": stored_filename,
        "created_at": _now_iso(),
    }

    profile.setdefault("samples", []).append(sample)
    profile["duration_s"] = round(sum(float(sample_info.get("duration_s", 0.0)) for sample_info in profile["samples"]), 2)
    saved = _save_profile(profile)
    logger.info("Voice sample added: %s (%s)", voice_id, sample_id)
    return sample


def delete_voice_profile(voice_id: str, ip_hash: str) -> bool:
    """Delete voice profile and all associated files. Returns True if deleted."""
    d = _voice_dir(voice_id)
    if not d.exists():
        return False
    shutil.rmtree(d)
    _write_audit(voice_id, "voice_deleted", ip_hash)
    logger.info("Voice profile deleted: %s", voice_id)
    return True


def get_reference_wav(voice_id: str) -> Optional[Path]:
    path = _reference_path(voice_id)
    return path if path.exists() else None


def reference_wav_path(voice_id: str) -> Path:
    return _reference_path(voice_id)


# ─── Audit Log ───────────────────────────────────────────────────────────────

def _write_audit(voice_id: str, action: str, ip_hash: str) -> None:
    entry = {
        "ts": _now_iso(),
        "voice_id": voice_id,
        "action": action,
        "ip_hash": ip_hash,
    }
    try:
        with open(settings.audit_log, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning("Failed to write audit log: %s", e)


def hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]
