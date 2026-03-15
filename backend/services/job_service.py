"""
Job queue: asyncio + ThreadPoolExecutor, JSON state persistence.
State machine: queued → processing → completed | failed
"""
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="inference")
_jobs: dict[str, dict] = {}  # in-memory cache

VALID_STATUSES = {"queued", "processing", "completed", "failed"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(job_id: str) -> Path:
    return settings.jobs_dir / f"{job_id}.json"


def _save_job(job: dict) -> None:
    _jobs[job["job_id"]] = job
    try:
        _job_path(job["job_id"]).write_text(json.dumps(job, indent=2))
    except Exception as e:
        logger.warning("Failed to persist job %s: %s", job["job_id"], e)


def _load_jobs_from_disk() -> None:
    """Restore job state from disk on startup."""
    for path in settings.jobs_dir.glob("*.json"):
        try:
            job = json.loads(path.read_text())
            _jobs[job["job_id"]] = job
            # Mark in-flight jobs as failed (they lost state during restart)
            if job["status"] == "processing":
                job["status"] = "failed"
                job["error"] = "Server restarted during processing"
                _save_job(job)
        except Exception as e:
            logger.warning("Failed to load job file %s: %s", path, e)


def create_job(voice_id: str, script: str, speed: float, pause_ms: int) -> dict:
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "voice_id": voice_id,
        "script": script,
        "speed": speed,
        "pause_ms": pause_ms,
        "status": "queued",
        "progress_pct": 0,
        "output_id": None,
        "error": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    _save_job(job)
    logger.info("Job created: %s", job_id)
    return job


def get_job(job_id: str) -> Optional[dict]:
    if job_id in _jobs:
        return _jobs[job_id]
    path = _job_path(job_id)
    if path.exists():
        job = json.loads(path.read_text())
        _jobs[job_id] = job
        return job
    return None


def list_jobs() -> list[dict]:
    return sorted(_jobs.values(), key=lambda j: j.get("created_at", ""), reverse=True)


def update_job(job_id: str, **kwargs) -> dict:
    job = get_job(job_id)
    if not job:
        raise KeyError(f"Job not found: {job_id}")
    job.update(kwargs)
    job["updated_at"] = _now_iso()
    _save_job(job)
    return job


def submit_job(job_id: str) -> None:
    """Submit job to thread pool for async execution."""
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_job, job_id)


def _run_job(job_id: str) -> None:
    """Worker: runs in thread pool."""
    job = get_job(job_id)
    if not job:
        logger.error("Job not found for execution: %s", job_id)
        return

    update_job(job_id, status="processing", progress_pct=5)

    try:
        from backend.services.audio_pipeline import run_synthesis_pipeline
        from backend.services.voice_service import get_reference_wav
        from backend.services.output_service import create_output

        ref_wav = get_reference_wav(job["voice_id"])
        if ref_wav is None:
            raise FileNotFoundError(f"Reference WAV not found for voice {job['voice_id']}")

        output_id = str(uuid.uuid4())
        output_dir = settings.outputs_dir / output_id

        def progress_cb(pct: float) -> None:
            update_job(job_id, progress_pct=int(5 + pct * 90))

        wav_path, mp3_path, duration_s = run_synthesis_pipeline(
            reference_wav=ref_wav,
            script=job["script"],
            output_dir=output_dir,
            speed=job["speed"],
            pause_ms=job["pause_ms"],
            progress_cb=progress_cb,
        )

        create_output(
            output_id=output_id,
            job_id=job_id,
            voice_id=job["voice_id"],
            script=job["script"],
            speed=job["speed"],
            pause_ms=job["pause_ms"],
            duration_s=duration_s,
        )

        update_job(
            job_id,
            status="completed",
            progress_pct=100,
            output_id=output_id,
        )
        logger.info("Job completed: %s → output %s (%.1fs)", job_id, output_id, duration_s)

    except Exception as e:
        logger.exception("Job failed: %s", job_id)
        update_job(job_id, status="failed", error=str(e), progress_pct=0)
