# Vuclear

**Create more. Record less.**

Vuclear is a creator-first, local-first voice tool for turning your own voice into usable, flexible audio for content and production.

## Project structure

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
```

Frontend:

```bash
cd frontend
npm install
```

Run:

```bash
# Terminal 1 - Backend
uvicorn backend.main:app --port 8000

# Terminal 2 - Frontend  
cd frontend && npm run dev
```

Then open:

- http://localhost:3000 (frontend)
- http://localhost:8000 (API docs)
- http://localhost:8000/docs (API reference)

## Development

### Quick Start (Recommended)

Just run:

```bash
./start.sh
```

Or on Windows:

```cmd
start.bat
```

### Environment Variables

Copy `.env.example` to `.env` and configure as needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `VOICE_ENGINE` | Voice engine to use | `chatterbox` |
| `MODEL_CACHE_DIR` | Where to cache models | `./models` |
| `OUTPUT_DIR` | Where to save outputs | `./outputs` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Supported Voice Engines

| Engine | Install | License |
|--------|---------|---------|
| Chatterbox TTS | `pip install chatterbox-tts` | Commercial OK |
| MetaVoice | `pip install metavoice` | Personal use |
| F5-TTS | `pip install f5-tts` | Non-commercial |

## API

### Synthesis

```bash
curl -X POST http://localhost:8000/api/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "voice_id": "default",
    "engine": "chatterbox"
  }'
```

### Voices

```bash
# List available voices
curl http://localhost:8000/api/voices
```

## Troubleshooting

### Python version error

If you see a Python version error, ensure you have Python 3.11-3.13:

```bash
python3 --version  # Should show 3.11, 3.12, or 3.13
```

### Port already in use

If port 8000 or 3000 is busy, specify different ports:

```bash
uvicorn backend.main:app --port 8001
cd frontend && npm run dev -- -p 3001
```

## License

MIT
