# Vuclear Quick Start

**Turn your voice into AI-generated audio in minutes.**

## One-Command Startup

### Mac / Linux / WSL

```bash
cd voice-cloner
./start.sh
```

### Windows

```cmd
cd voice-cloner
start.bat
```

This will:
1. Check your dependencies (Python, Node, FFmpeg)
2. Set up the Python environment if needed
3. Install frontend dependencies
4. Start both backend (port 8000) and frontend (port 3000)

---

## First Run

After startup, open your browser:

| Page | URL | Purpose |
|------|-----|---------|
| Voice Setup | http://localhost:3000 | Upload or record your voice |
| Studio | http://localhost:3000/studio | Generate audio with your voice |
| History | http://localhost:3000/history | View past generations |

### Step 1: Create a Voice Profile

1. Go to http://localhost:3000
2. Choose **Upload File** or **Record Mic**
3. Upload a 5-30 second audio clip of yourself speaking
4. Give it a name (e.g., "My Voice")
5. Check the consent box (you must own or have permission to clone the voice)
6. Click **Save Voice Profile**

### Step 2: Generate Audio

1. Go to http://localhost:3000/studio
2. Select your voice profile from the dropdown
3. Enter the script you want to generate
4. Adjust speed (0.7x - 1.3x) and pause length if needed
5. Click **Generate Audio**
6. Wait for processing to complete (progress bar shows status)
7. Play the generated audio or download as WAV/MP3

---

## Troubleshooting

### "Command not found" errors

Install dependencies:

**macOS:**
```bash
brew install python node ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install python3 nodejs npm ffmpeg
```

**Windows:**
- Python: https://python.org (check "Add to PATH")
- Node.js: https://nodejs.org
- FFmpeg: https://ffmpeg.org (or `choco install ffmpeg` with Chocolatey)

### Voice engine not found

If you see "No voice engine installed", install Chatterbox:

```bash
pip install chatterbox-tts
```

### Port already in use

If ports 3000 or 8000 are busy, stop other services or change the port in `.env`.

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|--------------|
| Python | 3.11 | 3.11-3.13 |
| Node.js | 20 | 22+ |
| RAM | 8GB | 16GB+ |
| GPU | Optional | NVIDIA 8GB+ VRAM |

**Voice engines** (install one):
- **Chatterbox** (default, MIT license, commercial OK)
- MetaVoice (Apache 2.0, commercial OK)
- F5-TTS (non-commercial only)

---

## Need Help?

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health
