"""
Audio pipeline: preprocessing, inference, post-processing, export.

INPUT  → normalize → trim silence → [denoise] → reference.wav
SCRIPT → chunk → synthesize per chunk → concat → loudness norm → WAV + MP3
"""
import logging
import json
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


def _parse_ffprobe_duration_tag(value: str) -> float | None:
    try:
        hours, minutes, seconds = value.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (AttributeError, TypeError, ValueError):
        return None


def _decode_audio_duration(path: Path) -> float:
    """
    Decode audio to PCM WAV and derive duration from sample count.
    This is the final fallback when container metadata is incomplete.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = Path(tmp.name)

    cmd = [
        "ffmpeg", "-y", "-i", str(path),
        "-vn",
        "-acodec", "pcm_s16le",
        str(tmp_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tmp_wav.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg decode failed: {result.stderr}")

    try:
        info = sf.info(str(tmp_wav))
        if info.samplerate <= 0 or info.frames <= 0:
            raise ValueError("Decoded audio has no measurable samples")
        duration = info.frames / info.samplerate
        logger.info(
            "Audio duration detected via decoded PCM fallback | path=%s duration_s=%.3f",
            path,
            duration,
        )
        return duration
    finally:
        tmp_wav.unlink(missing_ok=True)


def get_audio_duration(path: Path) -> float:
    """Return audio duration in seconds using layered metadata and decode fallbacks."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(
            "ffprobe failed for duration detection | path=%s stderr=%s",
            path,
            result.stderr.strip(),
        )
        return _decode_audio_duration(path)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.warning("ffprobe returned invalid JSON | path=%s error=%s", path, e)
        return _decode_audio_duration(path)

    for stream in data.get("streams", []):
        duration_value = stream.get("duration")
        if duration_value not in (None, "N/A"):
            duration = float(duration_value)
            logger.info(
                "Audio duration detected via ffprobe stream.duration | path=%s duration_s=%.3f",
                path,
                duration,
            )
            return duration
        tags = stream.get("tags") or {}
        for key in ("DURATION", "duration"):
            tagged_duration = _parse_ffprobe_duration_tag(tags.get(key))
            if tagged_duration is not None:
                logger.info(
                    "Audio duration detected via ffprobe stream.tags.%s | path=%s duration_s=%.3f",
                    key,
                    path,
                    tagged_duration,
                )
                return tagged_duration

    format_data = data.get("format") or {}
    format_duration_value = format_data.get("duration")
    if format_duration_value not in (None, "N/A"):
        duration = float(format_duration_value)
        logger.info(
            "Audio duration detected via ffprobe format.duration | path=%s duration_s=%.3f",
            path,
            duration,
        )
        return duration

    logger.info(
        "Audio duration metadata missing; falling back to decoded PCM measurement | path=%s",
        path,
    )
    return _decode_audio_duration(path)


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
        "audio/webm", "video/webm",
        "audio/mp4", "audio/x-m4a",
        "video/mp4",  # some m4a files report as mp4
    }
    if mime not in allowed_mimes:
        raise ValueError(
            f"Unsupported file type: {mime}. Upload WAV, MP3, OGG, WebM, M4A, or FLAC."
        )

    duration = get_audio_duration(path)
    if duration < 5:
        raise ValueError(f"Audio too short ({duration:.1f}s). Minimum 5 seconds required.")
    if duration > 120:
        raise ValueError(f"Audio too long ({duration:.1f}s). Maximum 120 seconds for reference.")

    return mime, duration


# ─── Script Processing ────────────────────────────────────────────────────────

def split_script(text: str, chunk_size: int = CHUNK_MAX_CHARS) -> list[str]:
    """Split script into synthesis chunks at sentence boundaries."""
    def split_long_sentence(sentence: str) -> list[str]:
        words = sentence.split()
        if not words:
            return []

        parts: list[str] = []
        current_part = ""

        for word in words:
            if not current_part:
                current_part = word
            elif len(current_part) + 1 + len(word) <= chunk_size:
                current_part += " " + word
            else:
                parts.append(current_part)
                current_part = word

        if current_part:
            parts.append(current_part)

        return parts

    # Split on sentence endings
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > chunk_size:
            if current:
                chunks.append(current)
                current = ""

            long_parts = split_long_sentence(sentence)
            if not long_parts:
                continue

            chunks.extend(long_parts[:-1])
            current = long_parts[-1]
            continue

        if not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= chunk_size:
            current += " " + sentence
        else:
            chunks.append(current)
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
