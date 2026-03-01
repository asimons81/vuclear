# Voice Cloner

Local-first voice cloning. Upload or record a 5–30s voice sample, type a script, download WAV + MP3 output.

**Zero cloud dependencies by default** — runs fully on your machine. GPU recommended (RTX 3060 8GB+), CPU fallback works (~10–20x slower).

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- `ffmpeg` in PATH (`apt install ffmpeg` / `brew install ffmpeg`)
- CUDA 12+ optional (for GPU acceleration)

```bash
git clone <repo> && cd voice-cloner

# Backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# Install voice engine (choose one — see Licensing section)
pip install chatterbox-tts           # MIT, default, English-focused
# pip install git+https://github.com/resemble-ai/chatterbox.git  # from source

# Download model weights
python scripts/download_models.py --engine chatterbox

# Configure
cp .env.example .env
# Edit .env: set VOICE_ENGINE, DATA_DIR, etc.

# Start backend (port 8000)
uvicorn backend.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev   # → http://localhost:3000
```

### Docker (optional)

```bash
docker compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Engine Selection

Set `VOICE_ENGINE` in `.env` to select your engine:

| Engine value | Model | Weights License | Commercial? | VRAM |
|---|---|---|---|---|
| `chatterbox` | Chatterbox Turbo/Multi | **MIT** | ✅ Yes | 8 GB |
| `metavoice` | MetaVoice-1B | **Apache 2.0** | ✅ Yes | 10–12 GB |
| `f5_noncommercial` | F5-TTS | **CC-BY-NC-4.0** | ❌ **No** | 6–8 GB |

```bash
# .env
VOICE_ENGINE=chatterbox     # default — MIT, commercial OK
# VOICE_ENGINE=metavoice    # Apache 2.0, commercial OK, needs more VRAM
# VOICE_ENGINE=f5_noncommercial  # CC-BY-NC — personal/research ONLY
```

---

## Licensing

### Application Code

The source code in this repository is licensed under the **MIT License** — you may use, modify, and distribute it freely, including in commercial products.

### Model Weights (read carefully)

Model weights have **separate licenses** from the code. Your legal obligations depend on which engine you activate:

#### `chatterbox` (default) — MIT
- **Weights**: MIT License
- **Commercial use**: ✅ Allowed
- **Source**: [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox)
- **Note**: Outputs contain a built-in Perth perceptual watermark for content authenticity

#### `metavoice` — Apache 2.0
- **Weights**: Apache 2.0 License
- **Commercial use**: ✅ Allowed
- **Source**: [metavoiceio/metavoice-src](https://github.com/metavoiceio/metavoice-src)
- **Note**: Requires 10–12GB VRAM

#### `f5_noncommercial` — CC-BY-NC-4.0 ⚠️
- **Weights**: [CC-BY-NC-4.0](https://creativecommons.org/licenses/by-nc/4.0/) — **NON-COMMERCIAL ONLY**
- **Commercial use**: ❌ **Prohibited** — you may not use this engine in any SaaS, paid product, or commercial service
- **Source**: [SWivid/F5-TTS on HuggingFace](https://huggingface.co/SWivid/F5-TTS)
- **For commercial use**: switch to `chatterbox` (MIT) or `metavoice` (Apache 2.0)

### What "commercial use" means here

Commercial use includes: selling access to generated audio, embedding in a paid SaaS product, offering as a paid API, or any use where the primary purpose is generating revenue. Personal use, research, and open-source projects without a commercial component are generally non-commercial.

When in doubt, consult a lawyer and review the specific license terms.

---

## Voice Consent

> This software requires explicit consent before any voice is cloned.

- You must own the voice you are cloning, or have explicit written permission from the voice's owner.
- Never use generated audio to deceive, impersonate, or harm anyone.
- Never clone a voice without authorization — doing so may be illegal in your jurisdiction.
- By using this software you take full responsibility for how generated audio is used.

The consent flag is stored in each voice profile's `profile.json` for auditability.

---

## API Reference

Base URL: `http://localhost:8000`

```
POST   /api/v1/voices                      Upload voice sample
GET    /api/v1/voices                      List voice profiles
DELETE /api/v1/voices/{voice_id}           Delete voice profile

POST   /api/v1/synthesize                  Queue synthesis job
GET    /api/v1/jobs/{job_id}               Poll job status
GET    /api/v1/jobs                        List all jobs

GET    /api/v1/outputs                     List completed outputs
GET    /api/v1/outputs/{id}/download?format=wav|mp3
DELETE /api/v1/outputs/{id}               Delete output

GET    /api/v1/health                      Engine status + GPU info
```

Swagger UI: `http://localhost:8000/docs`

---

## Audio Pipeline

```
Reference audio
  → ffmpeg → 16kHz mono WAV
  → librosa.effects.trim (silence removal)
  → [optional] DeepFilterNet3 denoising (DENOISE=true)

Script
  → sentence split → 200-char chunks
  → VoiceModel.synthesize() per chunk (in ThreadPool)
  → concatenate with pause_ms silence between chunks
  → resample to 44100 Hz
  → pyloudnorm → -14 LUFS (streaming standard)
  → clip guard: max ±0.99
  → soundfile → 24-bit WAV
  → ffmpeg → 192kbps MP3
```

---

## Testing

```bash
# Unit tests
pytest tests/ -v

# CLI inference test (requires model loaded)
python scripts/test_inference.py \
  --ref path/to/reference.wav \
  --text "Hello, this is a voice cloning test." \
  --output test_output.wav

# Objective quality checks
python tests/eval/run_checks.py --output test_output.wav --script "Hello..."

# Full output matrix check
python tests/eval/run_checks.py --full-matrix --results-json results.json

# WER evaluation (requires: pip install openai-whisper jiwer)
python tests/eval/run_wer.py --output test_output.wav --script "Hello..."
```

### Quality Targets

| Check | Target |
|---|---|
| No clipping | Peak < 0.99 |
| Loudness | -16 to -12 LUFS |
| Leading/trailing silence | < 1 second |
| WAV/MP3 format valid | ffprobe passes |
| WER (Whisper tiny) | < 5% |

---

## Deployment Options (Free Tier)

| Platform | GPU | Notes |
|---|---|---|
| **Render.com** | CPU only | FastAPI hosting (free tier) |
| **Modal.com** | A10G / T4 | $30/mo free credit — best for inference |
| **Vercel** | — | Frontend only |
| **HuggingFace Spaces** | CPU only | Too slow for inference; good for demo UI |

**Recommended free setup**: Frontend on Vercel + FastAPI on Render + inference worker on Modal.

---

## Data Layout

```
data/
  voices/{voice_id}/
    reference.wav          # normalized 16kHz mono
    profile.json           # {name, consent, created_at, duration_s, engine}
  outputs/{output_id}/
    output.wav             # 24-bit 44.1kHz
    output.mp3             # 192kbps
    meta.json              # {voice_id, script, speed, pause_ms, duration_s}
  jobs/{job_id}.json       # {status, progress_pct, output_id, error}
  audit.jsonl              # append-only consent/action log (ip_hash, not plain IP)
```

---

## Environment Variables

See `.env.example` for all options:

| Variable | Default | Description |
|---|---|---|
| `VOICE_ENGINE` | `chatterbox` | Engine: `chatterbox`, `metavoice`, `f5_noncommercial` |
| `DATA_DIR` | `./data` | Where to store voices, outputs, jobs |
| `DENOISE` | `false` | Enable DeepFilterNet3 denoising (`pip install deepfilternet`) |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |
| `RATE_LIMIT_VOICE_UPLOAD` | `10/hour` | Per-IP upload limit |
| `RATE_LIMIT_SYNTHESIZE` | `20/hour` | Per-IP synthesis limit |

---

## Commercial Launch Checklist

If you're building a commercial product on top of this:

- [ ] Use only `chatterbox` (MIT) or `metavoice` (Apache 2.0) — never `f5_noncommercial`
- [ ] Add DMCA takedown process for voice impersonation reports
- [ ] Consider voice ID verification for high-risk use cases
- [ ] Document watermarking (Chatterbox Perth watermark) in your ToS
- [ ] Review jurisdiction-specific laws on synthetic voice (EU AI Act, US state laws)
- [ ] Consider adding AudioSeal or similar watermarking if switching from Chatterbox
