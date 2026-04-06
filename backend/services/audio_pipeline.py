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

from backend.services.effects import apply_effects

logger = logging.getLogger(__name__)

TARGET_SR = 44100          # Output sample rate
TARGET_LUFS = -14.0        # Streaming standard (Spotify/YouTube target)
CHUNK_MAX_CHARS = 800
LONG_FORM_MAX_CHARS = 50000
DEFAULT_CROSSFADE_MS = 120
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

_ABBREVIATION_MARKERS = {
    "Dr.": "Dr<prd>",
    "Mr.": "Mr<prd>",
    "Mrs.": "Mrs<prd>",
    "Ms.": "Ms<prd>",
    "Prof.": "Prof<prd>",
    "Sr.": "Sr<prd>",
    "Jr.": "Jr<prd>",
    "St.": "St<prd>",
    "vs.": "vs<prd>",
    "etc.": "etc<prd>",
    "e.g.": "e<prd>g<prd>",
    "i.e.": "i<prd>e<prd>",
    "U.S.": "U<prd>S<prd>",
    "U.K.": "U<prd>K<prd>",
}

_SENTENCE_ENDINGS = {".", "!", "?", "。", "！", "？"}


def _protect_abbreviations(text: str) -> str:
    protected = text
    for abbreviation, marker in sorted(_ABBREVIATION_MARKERS.items(), key=lambda item: len(item[0]), reverse=True):
        protected = protected.replace(abbreviation, marker)
    return protected


def _restore_abbreviations(text: str) -> str:
    restored = text
    for abbreviation, marker in _ABBREVIATION_MARKERS.items():
        restored = restored.replace(marker, abbreviation)
    return restored


def _split_long_sentence(sentence: str, chunk_size: int) -> list[str]:
    sentence = sentence.strip()
    if not sentence:
        return []

    if " " not in sentence:
        return [sentence[i : i + chunk_size] for i in range(0, len(sentence), chunk_size)]

    words = sentence.split()
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


def split_script(text: str, chunk_size: int = CHUNK_MAX_CHARS) -> list[str]:
    """Split script into synthesis chunks at sentence boundaries.

    Handles common abbreviations, CJK punctuation, and bracketed tags.
    """
    protected_text = _protect_abbreviations(text.strip())
    if not protected_text:
        return []

    sentences: list[str] = []
    current = ""

    for index, char in enumerate(protected_text):
        current += char
        if char not in _SENTENCE_ENDINGS:
            continue

        if char == ".":
            prev_char = protected_text[index - 1] if index > 0 else ""
            next_char = protected_text[index + 1] if index + 1 < len(protected_text) else ""
            if prev_char.isdigit() and next_char.isdigit():
                continue
            if next_char == ".":
                continue

        sentence = _restore_abbreviations(current.strip())
        if sentence:
            sentences.append(sentence)
        current = ""

    trailing = _restore_abbreviations(current.strip())
    if trailing:
        sentences.append(trailing)

    def can_merge_sentence(sentence_text: str) -> bool:
        has_cjk = bool(re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uf900-\ufaff]", sentence_text))
        starts_with_tag = bool(re.match(r"^\[[^\]]+\]", sentence_text))
        return not has_cjk and not starts_with_tag

    chunks: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        if len(sentence) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            long_parts = _split_long_sentence(sentence, chunk_size)
            chunks.extend(part for part in long_parts if part.strip())
            continue

        sentence = sentence.strip()
        if not sentence:
            continue

        if not current_chunk:
            current_chunk = sentence
            continue

        if can_merge_sentence(current_chunk) and can_merge_sentence(sentence) and len(current_chunk) + 1 + len(sentence) <= chunk_size:
            current_chunk += " " + sentence
        else:
            chunks.append(current_chunk)
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return [chunk for chunk in chunks if chunk.strip()]


def join_audio_chunks_with_crossfade(
    chunks: list[np.ndarray],
    *,
    sample_rate: int,
    crossfade_ms: int = DEFAULT_CROSSFADE_MS,
) -> np.ndarray:
    """Join mono chunks with an overlap crossfade."""
    if not chunks:
        return np.array([], dtype=np.float32)

    arrays = [np.asarray(chunk, dtype=np.float32).ravel() for chunk in chunks if np.asarray(chunk).size]
    if not arrays:
        return np.array([], dtype=np.float32)
    if len(arrays) == 1:
        return arrays[0].astype(np.float32, copy=False)

    crossfade_samples = int(sample_rate * max(0, crossfade_ms) / 1000)
    crossfade_samples = min(crossfade_samples, *(len(chunk) for chunk in arrays)) if crossfade_samples > 0 else 0
    if crossfade_samples < 2:
        return np.concatenate(arrays).astype(np.float32, copy=False)

    fade_in = np.linspace(0.0, 1.0, crossfade_samples, dtype=np.float32)
    fade_out = 1.0 - fade_in

    output = arrays[0]
    for chunk in arrays[1:]:
        overlap = output[-crossfade_samples:] * fade_out + chunk[:crossfade_samples] * fade_in
        output = np.concatenate([output[:-crossfade_samples], overlap, chunk[crossfade_samples:]])

    return np.clip(output, -1.0, 1.0).astype(np.float32, copy=False)


# ─── Full Synthesis Pipeline ──────────────────────────────────────────────────

def run_synthesis_pipeline(
    reference_wav: Path,
    script: str,
    output_dir: Path,
    speed: float = 1.0,
    pause_ms: int = 300,
    effects_preset: str | None = None,
    chunk_size: int = CHUNK_MAX_CHARS,
    crossfade_ms: int = DEFAULT_CROSSFADE_MS,
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

    if len(script.strip()) > LONG_FORM_MAX_CHARS:
        raise ValueError(f"Script too long ({len(script.strip())} chars). Maximum {LONG_FORM_MAX_CHARS} characters.")

    chunks = split_script(script, chunk_size=chunk_size)
    if not chunks:
        raise ValueError("Script is empty after processing")

    logger.info("Synthesizing %d chunks for script of %d chars", len(chunks), len(script))

    audio_segments: list[np.ndarray] = []
    model_sr = model.SAMPLE_RATE

    # Silence padding between chunks is only used when crossfade is disabled.
    pause_samples = int(model_sr * pause_ms / 1000)
    silence = np.zeros(pause_samples, dtype=np.float32)

    for i, chunk in enumerate(chunks):
        logger.debug("Chunk %d/%d: %r", i + 1, len(chunks), chunk[:60])
        chunk_audio = model.synthesize(text=chunk, reference_wav=reference_wav, speed=speed)
        audio_segments.append(chunk_audio)
        if i < len(chunks) - 1 and crossfade_ms <= 0:
            audio_segments.append(silence)

        if progress_cb:
            progress_cb((i + 1) / len(chunks) * 0.8)  # 0–80% for synthesis

    # Concatenate with overlap crossfade when enabled.
    if crossfade_ms > 0:
        combined = join_audio_chunks_with_crossfade(audio_segments, sample_rate=model_sr, crossfade_ms=crossfade_ms)
    else:
        combined = np.concatenate(audio_segments)

    # Resample to 44100 Hz
    if model_sr != TARGET_SR:
        combined = librosa.resample(combined, orig_sr=model_sr, target_sr=TARGET_SR)

    if effects_preset:
        combined = apply_effects(combined, TARGET_SR, preset=effects_preset)

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
