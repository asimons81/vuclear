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
) -> dict:
    meta = {
        "output_id": output_id,
        "job_id": job_id,
        "voice_id": voice_id,
        "script": script,
        "speed": speed,
        "pause_ms": pause_ms,
        "duration_s": round(duration_s, 2),
        "created_at": _now_iso(),
    }
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
