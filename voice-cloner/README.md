# Vuclear

Vuclear is a creator-first voice tool that helps people turn their own voice into usable, flexible audio for content, iteration, and production — with speed, control, and consent at the center.

## Real project structure

The actual application root is this nested directory:

`voice-cloner`

Key folders:

- `backend/`: FastAPI service, synthesis pipeline, CLI, storage/services layer
- `frontend/`: existing Next.js UI
- `docs/`: audit, CLI usage, service contract, pipeline readiness notes
- `tests/`: lightweight automated tests and evaluation helpers

## Quick setup

Prerequisites:

- `python3` 3.11+
- Node.js 20+
- `ffmpeg` and `ffprobe` in `PATH`
- one supported voice engine installed locally

Backend:

```bash
cd vuclear
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Choose one engine
pip install chatterbox-tts
# or: pip install metavoice
# or: pip install f5-tts   # non-commercial only

cp .env.example .env
uvicorn backend.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## One-command narration

CLI:

```bash
python3 -m backend.cli synth --voice <voice_id> --script-file ./script.txt --json
```

API:

```bash
curl -s http://localhost:8000/api/v1/synthesize \
  -H 'Content-Type: application/json' \
  -d '{"voice_id":"<voice_id>","script":"Hello world","speed":1.0,"pause_ms":300}'
```

## Architecture overview

- `POST /api/v1/voices` ingests reference audio, validates it, normalizes it to `reference.wav`, and stores `profile.json`.
- `POST /api/v1/synthesize` creates a persisted job under `data/jobs/<job_id>/job.json` and runs synthesis in the local executor.
- Successful jobs publish finalized artifacts under `data/outputs/<job_id>/`.
- Each job also writes lifecycle events to `data/jobs/<job_id>/events.jsonl`.
- Completed outputs emit `metadata.json` plus `timings.json` with chunk-level timing data.
- `python3 -m backend.cli` uses the same backend services directly, so agents do not need the frontend.

## Storage layout

```text
data/
  voices/<voice_id>/
    profile.json
    reference.wav
  jobs/<job_id>/
    job.json
    events.jsonl
  outputs/<job_id>/
    audio.wav
    audio.mp3
    metadata.json
    timings.json
  logs/
    service.log
    audit.jsonl
  tmp/
    jobs/<job_id>/
```

## Supported engines

| Engine | Env value | License | Commercial use |
|---|---|---|---|
| Chatterbox | `chatterbox` | MIT | Yes |
| MetaVoice | `metavoice` | Apache 2.0 | Yes |
| F5-TTS | `f5_noncommercial` | CC-BY-NC-4.0 | No |

`f5_noncommercial` is intentionally labeled as non-commercial. Do not use it in production or revenue-generating pipelines.

## Tests

Lightweight tests:

```bash
python3 -m pytest tests/test_api_service.py tests/test_cli.py tests/test_audio_pipeline.py -v
```

Optional/manual inference validation:

```bash
python3 scripts/test_inference.py --ref path/to/reference.wav --text "Hello world" --output test_output.wav
python3 tests/eval/run_checks.py --output test_output.wav
```

## Docs

- `docs/codex-audit-report.md`
- `docs/cli-usage.md`
- `docs/internal-service-contract.md`
- `docs/pipeline-readiness.md`
