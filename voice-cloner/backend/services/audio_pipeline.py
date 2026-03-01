"""
Audio pipeline: preprocessing, inference, post-processing, export.

INPUT  → normalize → trim silence → [denoise] → reference.wav
SCRIPT → chunk → synthesize per chunk → concat → loudness norm → WAV + MP3
"""
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf
import librosa
import pyloudnorm as pyln

logger = logging.getLogger(__name__)

TARGET_SR = 44100          # Output sample rate
TARGET_LUFS = -14.0        # Streaming standard (Spotify/YouTube target)
CHUNK_MAX_CHARS = 200
REFERENCE_SR = 16000       # Model input sample rate


# ─── Reference Audio Preprocessing ───────────────────────────────────────────

def preprocess_reference(input_path: Path, output_path: Path, denoise: bool = False) -> float:
    """
    Normalize reference audio to 16kHz mono WAV.
    Returns duration in seconds of the cleaned audio.
    """
    # Step 1: ffmpeg convert to 16kHz mono 16-bit WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ar", str(REFERENCE_SR),
        "-ac", "1",
        "-acodec", "pcm_s16le",
        str(tmp_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    # Step 2: Load and trim silence
    audio, sr = librosa.load(str(tmp_path), sr=REFERENCE_SR, mono=True)
    audio, _ = librosa.effects.trim(audio, top_db=30)

    if len(audio) < REFERENCE_SR * 5:
        raise ValueError("Reference audio too short after silence trim (need ≥5s of speech)")

    # Step 3: Optional denoising
    if denoise:
        audio = _apply_deepfilter(audio, sr)

    # Step 4: Save
    sf.write(str(output_path), audio, REFERENCE_SR, subtype="PCM_16")
    tmp_path.unlink(missing_ok=True)

    duration = len(audio) / REFERENCE_SR
    logger.info("Reference preprocessed: %.1fs at %dHz", duration, REFERENCE_SR)
    return duration


def _apply_deepfilter(audio: np.ndarray, sr: int) -> np.ndarray:
    try:
        from df.enhance import enhance, init_df
        model, df_state, _ = init_df()
        import torch
        tensor = torch.from_numpy(audio).unsqueeze(0)
        enhanced = enhance(model, df_state, tensor)
        return enhanced.squeeze().numpy()
    except ImportError:
        logger.warning("DeepFilterNet not installed; skipping denoise. pip install deepfilternet")
        return audio
    except Exception as e:
        logger.warning("Denoising failed (%s); continuing without it", e)
        return audio


def get_audio_duration(path: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    import json
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if "duration" in stream:
            return float(stream["duration"])
    raise ValueError("No duration found in ffprobe output")


def validate_audio_file(path: Path) -> tuple[str, float]:
    """
    Validate file type via magic bytes and get duration.
    Returns (mime_type, duration_seconds).
    Raises ValueError on invalid files.
    """
    try:
        import magic
        mime = magic.from_file(str(path), mime=True)
    except ImportError:
        logger.warning("python-magic not installed; skipping MIME check")
        mime = "audio/unknown"

    allowed_mimes = {
        "audio/mpeg", "audio/mp3",
        "audio/wav", "audio/x-wav",
        "audio/ogg", "audio/flac",
        "audio/mp4", "audio/x-m4a",
        "video/mp4",  # some m4a files report as mp4
    }
    if mime not in allowed_mimes:
        raise ValueError(f"Unsupported file type: {mime}. Upload WAV, MP3, OGG, M4A, or FLAC.")

    duration = get_audio_duration(path)
    if duration < 5:
        raise ValueError(f"Audio too short ({duration:.1f}s). Minimum 5 seconds required.")
    if duration > 120:
        raise ValueError(f"Audio too long ({duration:.1f}s). Maximum 120 seconds for reference.")

    return mime, duration


# ─── Script Processing ────────────────────────────────────────────────────────

def split_script(text: str, chunk_size: int = CHUNK_MAX_CHARS) -> list[str]:
    """Split script into synthesis chunks at sentence boundaries."""
    # Split on sentence endings
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= chunk_size:
            current += " " + sentence
        else:
            chunks.append(current)
            # If single sentence exceeds chunk_size, split by words
            if len(sentence) > chunk_size:
                words = sentence.split()
                current = ""
                for word in words:
                    if len(current) + 1 + len(word) <= chunk_size:
                        current = (current + " " + word).strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = sentence

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


# ─── Full Synthesis Pipeline ──────────────────────────────────────────────────

def run_synthesis_pipeline(
    reference_wav: Path,
    script: str,
    output_dir: Path,
    speed: float = 1.0,
    pause_ms: int = 300,
    model=None,
    progress_cb: Callable[[float], None] | None = None,
) -> tuple[Path, Path, float]:
    """
    Full pipeline: chunk → synthesize → post-process → export.

    Returns (wav_path, mp3_path, duration_seconds).
    """
    from .model.factory import get_model
    if model is None:
        model = get_model()

    chunks = split_script(script)
    if not chunks:
        raise ValueError("Script is empty after processing")

    logger.info("Synthesizing %d chunks for script of %d chars", len(chunks), len(script))

    audio_segments: list[np.ndarray] = []
    model_sr = model.SAMPLE_RATE

    # Silence padding between chunks
    pause_samples = int(model_sr * pause_ms / 1000)
    silence = np.zeros(pause_samples, dtype=np.float32)

    for i, chunk in enumerate(chunks):
        logger.debug("Chunk %d/%d: %r", i + 1, len(chunks), chunk[:60])
        chunk_audio = model.synthesize(text=chunk, reference_wav=reference_wav, speed=speed)
        audio_segments.append(chunk_audio)
        if i < len(chunks) - 1:
            audio_segments.append(silence)

        if progress_cb:
            progress_cb((i + 1) / len(chunks) * 0.8)  # 0–80% for synthesis

    # Concatenate
    combined = np.concatenate(audio_segments)

    # Resample to 44100 Hz
    if model_sr != TARGET_SR:
        combined = librosa.resample(combined, orig_sr=model_sr, target_sr=TARGET_SR)

    # Loudness normalize to -14 LUFS
    meter = pyln.Meter(TARGET_SR)
    loudness = meter.integrated_loudness(combined)
    if not np.isinf(loudness):
        combined = pyln.normalize.loudness(combined, loudness, TARGET_LUFS)

    # Clip guard
    combined = np.clip(combined, -0.99, 0.99)

    duration = len(combined) / TARGET_SR
    logger.info("Synthesis complete: %.1fs of audio", duration)

    if progress_cb:
        progress_cb(0.9)

    # Export WAV (24-bit 44.1kHz)
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / "output.wav"
    mp3_path = output_dir / "output.mp3"

    sf.write(str(wav_path), combined, TARGET_SR, subtype="PCM_24")

    # Export MP3 192kbps via ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-i", str(wav_path),
        "-b:a", "192k",
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("MP3 export failed: %s", result.stderr)

    if progress_cb:
        progress_cb(1.0)

    return wav_path, mp3_path, duration
