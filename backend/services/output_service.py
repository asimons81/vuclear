"""Output metadata CRUD."""
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _output_dir(output_id: str) -> Path:
    return settings.outputs_dir / output_id


def _meta_path(output_id: str) -> Path:
    return _output_dir(output_id) / "meta.json"


def create_output(
    output_id: str,
    job_id: str,
    voice_id: str,
    script: str,
    speed: float,
    pause_ms: int,
    duration_s: float,
    chunk_size: int = 800,
    crossfade_ms: int = 120,
    effects_preset: str | None = None,
    generation_id: str | None = None,
    take_number: int = 1,
    lineage_job_id: str | None = None,
) -> dict:
    generation_id = generation_id or job_id
    lineage_job_id = lineage_job_id or generation_id
    meta = {
        "output_id": output_id,
        "job_id": job_id,
        "voice_id": voice_id,
        "script": script,
        "speed": speed,
        "pause_ms": pause_ms,
        "chunk_size": chunk_size,
        "crossfade_ms": crossfade_ms,
        "effects_preset": effects_preset,
        "generation_id": generation_id,
        "take_number": take_number,
        "lineage_job_id": lineage_job_id,
        "duration_s": round(duration_s, 2),
        "created_at": _now_iso(),
    }
    _output_dir(output_id).mkdir(parents=True, exist_ok=True)
    _meta_path(output_id).write_text(json.dumps(meta, indent=2))
    return meta


def get_output(output_id: str) -> Optional[dict]:
    path = _meta_path(output_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def list_outputs() -> list[dict]:
    outputs = []
    for meta_path in settings.outputs_dir.glob("*/meta.json"):
        try:
            outputs.append(json.loads(meta_path.read_text()))
        except Exception as e:
            logger.warning("Failed to read output meta %s: %s", meta_path, e)
    outputs.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    return outputs


def list_output_takes(generation_id: str) -> list[dict]:
    takes = [output for output in list_outputs() if output.get("generation_id") == generation_id]
    takes.sort(key=lambda o: int(o.get("take_number", 0)))
    return takes


def delete_output(output_id: str) -> bool:
    d = _output_dir(output_id)
    if not d.exists():
        return False
    shutil.rmtree(d)
    logger.info("Output deleted: %s", output_id)
    return True


def get_output_file(output_id: str, fmt: str) -> Optional[Path]:
    if fmt not in ("wav", "mp3"):
        raise ValueError("Format must be 'wav' or 'mp3'")
    path = _output_dir(output_id) / f"output.{fmt}"
    return path if path.exists() else None
