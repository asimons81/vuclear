# Internal Service Contract

This document defines how Ozzy or any other internal agent should call `vuclear`.

## Preferred interfaces

1. Local CLI: `python3 -m backend.cli`
2. Local HTTP API: `http://localhost:8000/api/v1/...`

The CLI and API use the same persisted backend services and storage layout.

## Inputs

Voice creation:

- reference audio file
- voice/profile name
- explicit consent flag

Narration request:

- `voice_id`
- `script`
- optional `speed`
- optional `pause_ms`

## Job lifecycle

Jobs use these statuses:

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

Every job persists:

- `job_id`
- `voice_id`
- `engine`
- `script_text`
- `audio_settings`
- `progress_pct`
- `error`
- `warnings`
- `attempt`
- `retry_of`
- `created_at`
- `started_at`
- `completed_at`

## API endpoints

Create voice:

```text
POST /api/v1/voices
```

Queue narration:

```text
POST /api/v1/synthesize
```

Poll job:

```text
GET /api/v1/jobs/{job_id}
GET /api/v1/jobs/{job_id}/events
POST /api/v1/jobs/{job_id}/retry
POST /api/v1/jobs/{job_id}/cancel
```

Read output:

```text
GET /api/v1/outputs
GET /api/v1/outputs/{output_id}
GET /api/v1/outputs/{output_id}/timings
GET /api/v1/outputs/{output_id}/download?format=wav|mp3
```

Health:

```text
GET /api/v1/health
```

## Output contract

Successful jobs produce:

- `data/outputs/<job_id>/audio.wav`
- `data/outputs/<job_id>/audio.mp3` when MP3 export succeeds
- `data/outputs/<job_id>/metadata.json`
- `data/outputs/<job_id>/timings.json`

`metadata.json` includes:

- `job_id`
- `voice_id`
- `engine`
- `request`
- `audio_settings`
- `duration`
- `paths`
- `checksums`
- `warnings`
- `errors`

`timings.json` currently provides chunk-level timing. This is suitable for downstream scene timing, subtitle chunking, and rough narration alignment.

## Failure modes

- invalid or missing voice profile
- missing reference audio
- engine import/load failure
- synthesis pipeline failure
- ffmpeg export failure
- cooperative cancellation
- stale/interrupted jobs after process restart

Failures are surfaced in:

- job `status`
- job `error`
- job event log
- `data/logs/service.log`

## Expectations for callers

- treat `job_id` as the stable handle for polling and downstream artifact lookup
- do not assume MP3 always exists; WAV is the primary artifact
- use `retry-job` or `POST /jobs/{job_id}/retry` rather than mutating old jobs
- read `warnings` and `errors` instead of assuming every success is perfectly clean
