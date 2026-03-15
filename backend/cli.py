"""Agent-friendly CLI for local Vuclear operations."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from backend.config import ensure_dirs
from backend.logging_setup import configure_logging
from backend.services import job_service, output_service, voice_service


logger = logging.getLogger(__name__)


def _emit(payload: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return

    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
        return

    for item in payload:
        print(item)


def _read_script(args: argparse.Namespace) -> str:
    if args.script:
        return args.script.strip()
    if args.script_file:
        return Path(args.script_file).read_text(encoding="utf-8").strip()
    raise SystemExit("Provide either --script or --script-file")


def cmd_health(args: argparse.Namespace) -> int:
    from backend.config import settings
    from backend.services.model.factory import get_model

    try:
        model = get_model()
        engine_loaded = model.is_loaded
        engine_license = model.LICENSE
        commercial_ok = model.COMMERCIAL_OK
    except Exception as exc:
        engine_loaded = False
        engine_license = None
        commercial_ok = None
        logger.warning("Health check could not load engine: %s", exc)

    payload = {
        "status": "ok",
        "engine": settings.voice_engine,
        "engine_loaded": engine_loaded,
        "engine_license": engine_license,
        "commercial_ok": commercial_ok,
        "data_dir": str(settings.data_dir.resolve()),
        "voices_dir": str(settings.voices_dir.resolve()),
        "jobs_dir": str(settings.jobs_dir.resolve()),
        "outputs_dir": str(settings.outputs_dir.resolve()),
        "logs_dir": str(settings.logs_dir.resolve()),
    }
    _emit(payload, as_json=args.json)
    return 0


def cmd_synth(args: argparse.Namespace) -> int:
    voice = voice_service.get_voice_profile(args.voice)
    if not voice:
        message = {"error": f"Voice not found: {args.voice}"}
        _emit(message, as_json=args.json)
        return 2

    script = _read_script(args)
    job = job_service.create_job(
        voice_id=args.voice,
        script=script,
        speed=args.speed,
        pause_ms=args.pause_ms,
    )
    job_service.submit_job(job["job_id"])

    if not args.wait:
        _emit({"job_id": job["job_id"], "status": job["status"]}, as_json=args.json)
        return 0

    try:
        final_job = job_service.wait_for_job(job["job_id"], timeout_s=args.timeout)
    except TimeoutError as exc:
        _emit({"job_id": job["job_id"], "status": "running", "error": str(exc)}, as_json=args.json)
        return 3

    payload: dict[str, Any] = {"job": final_job}
    if final_job.get("output_id"):
        payload["output"] = output_service.get_output(final_job["output_id"])

    _emit(payload, as_json=args.json)
    return 0 if final_job["status"] == "succeeded" else 1


def cmd_job_status(args: argparse.Namespace) -> int:
    job = job_service.get_job(args.job_id)
    if not job:
        _emit({"error": f"Job not found: {args.job_id}"}, as_json=args.json)
        return 2
    _emit(job, as_json=args.json)
    return 0


def cmd_retry_job(args: argparse.Namespace) -> int:
    try:
        job = job_service.create_retry_job(args.job_id)
    except KeyError:
        _emit({"error": f"Job not found: {args.job_id}"}, as_json=args.json)
        return 2

    job_service.submit_job(job["job_id"])
    _emit({"job_id": job["job_id"], "status": job["status"], "retry_of": args.job_id}, as_json=args.json)
    return 0


def cmd_cancel_job(args: argparse.Namespace) -> int:
    try:
        job = job_service.cancel_job(args.job_id)
    except KeyError:
        _emit({"error": f"Job not found: {args.job_id}"}, as_json=args.json)
        return 2
    _emit({"job_id": job["job_id"], "status": job["status"]}, as_json=args.json)
    return 0


def cmd_list_outputs(args: argparse.Namespace) -> int:
    _emit(output_service.list_outputs(), as_json=args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vuclear", description="Local voice cloning and narration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="Inspect local service readiness")
    health.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    health.set_defaults(func=cmd_health)

    synth = subparsers.add_parser("synth", help="Queue or run a synthesis job")
    synth.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    synth.add_argument("--voice", required=True, help="Voice profile ID")
    synth.add_argument("--script", help="Inline script text")
    synth.add_argument("--script-file", help="Path to script text file")
    synth.add_argument("--speed", type=float, default=1.0)
    synth.add_argument("--pause-ms", type=int, default=300)
    synth.add_argument("--timeout", type=float, default=300.0, help="Wait timeout in seconds")
    synth.add_argument("--wait", action=argparse.BooleanOptionalAction, default=True, help="Wait for terminal job state")
    synth.set_defaults(func=cmd_synth)

    job_status = subparsers.add_parser("job-status", help="Fetch a persisted job record")
    job_status.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    job_status.add_argument("job_id")
    job_status.set_defaults(func=cmd_job_status)

    retry_job = subparsers.add_parser("retry-job", help="Create a retry job from an existing job")
    retry_job.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    retry_job.add_argument("job_id")
    retry_job.set_defaults(func=cmd_retry_job)

    cancel_job = subparsers.add_parser("cancel-job", help="Request cancellation for a job")
    cancel_job.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    cancel_job.add_argument("job_id")
    cancel_job.set_defaults(func=cmd_cancel_job)

    list_outputs = subparsers.add_parser("list-outputs", help="List completed outputs")
    list_outputs.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    list_outputs.set_defaults(func=cmd_list_outputs)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    ensure_dirs()
    job_service._load_jobs_from_disk()

    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
