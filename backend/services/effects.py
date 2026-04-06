"""Lightweight audio effects chain for post-synthesis processing."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def _as_float32(audio: np.ndarray) -> np.ndarray:
    return np.asarray(audio, dtype=np.float32).copy()


def _normalize_peak(audio: np.ndarray, peak: float = 0.99) -> np.ndarray:
    max_abs = float(np.max(np.abs(audio))) if audio.size else 0.0
    if max_abs <= 0.0:
        return audio
    scale = min(1.0, peak / max_abs)
    return audio * scale


def _apply_gain(audio: np.ndarray, gain_db: float) -> np.ndarray:
    return audio * float(10 ** (gain_db / 20.0))


def _compress(audio: np.ndarray, threshold_db: float, ratio: float, makeup_db: float = 0.0) -> np.ndarray:
    # Simple feed-forward soft knee compressor in the time domain.
    eps = 1e-8
    abs_audio = np.maximum(np.abs(audio), eps)
    input_db = 20.0 * np.log10(abs_audio)
    over = input_db - threshold_db
    gain_reduction_db = np.where(over > 0.0, over - (over / ratio), 0.0)
    gain_db = makeup_db - gain_reduction_db
    return audio * (10 ** (gain_db / 20.0))


def _lowpass_filter(audio: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    if cutoff_hz <= 0:
        return audio
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)
    out = np.empty_like(audio)
    out[0] = audio[0]
    for i in range(1, len(audio)):
        out[i] = out[i - 1] + alpha * (audio[i] - out[i - 1])
    return out


def _highpass_filter(audio: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    if cutoff_hz <= 0:
        return audio
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)
    out = np.empty_like(audio)
    out[0] = audio[0]
    for i in range(1, len(audio)):
        out[i] = alpha * (out[i - 1] + audio[i] - audio[i - 1])
    return out


def _delay(audio: np.ndarray, sample_rate: int, delay_ms: float, mix: float, feedback: float = 0.0) -> np.ndarray:
    delay_samples = max(1, int(sample_rate * delay_ms / 1000.0))
    out = audio.copy()
    for i in range(delay_samples, len(audio)):
        out[i] += audio[i - delay_samples] * mix
        if feedback:
            out[i] += out[i - delay_samples] * feedback * 0.5
    return out


def _reverb(audio: np.ndarray, sample_rate: int, mix: float, decay: float) -> np.ndarray:
    # Two short taps for an inexpensive room-like tail.
    wet = _delay(audio, sample_rate, delay_ms=45.0, mix=mix * 0.6, feedback=decay * 0.35)
    wet = _delay(wet, sample_rate, delay_ms=87.0, mix=mix * 0.4, feedback=decay * 0.25)
    return wet


_PRESETS: dict[str, list[tuple[str, dict[str, float]]]] = {
    "dry": [],
    "telephone": [
        ("highpass", {"cutoff_hz": 300.0}),
        ("lowpass", {"cutoff_hz": 3400.0}),
        ("compress", {"threshold_db": -24.0, "ratio": 4.0, "makeup_db": 3.0}),
        ("gain", {"gain_db": 2.5}),
    ],
    "broadcast": [
        ("highpass", {"cutoff_hz": 90.0}),
        ("lowpass", {"cutoff_hz": 6500.0}),
        ("compress", {"threshold_db": -20.0, "ratio": 2.8, "makeup_db": 2.0}),
        ("gain", {"gain_db": 1.5}),
    ],
    "warm": [
        ("highpass", {"cutoff_hz": 70.0}),
        ("lowpass", {"cutoff_hz": 11000.0}),
        ("reverb", {"mix": 0.10, "decay": 0.25}),
    ],
    "cinematic": [
        ("gain", {"gain_db": 2.0}),
        ("compress", {"threshold_db": -18.0, "ratio": 2.5, "makeup_db": 1.0}),
        ("reverb", {"mix": 0.16, "decay": 0.45}),
        ("delay", {"delay_ms": 120.0, "mix": 0.10, "feedback": 0.10}),
    ],
}


def apply_effects(audio: np.ndarray, sample_rate: int, preset: str | None = None) -> np.ndarray:
    """Apply a named effects preset to mono audio.

    Presets are intentionally lightweight and local-only. They are designed to
    give the synthesized voice a usable character without introducing heavy new
    dependencies.
    """

    preset_name = (preset or "dry").strip().lower()
    if preset_name not in _PRESETS:
        raise ValueError(f"Unknown effects preset: {preset}")

    out = _as_float32(audio)
    if not out.size or preset_name == "dry":
        return out

    for effect_name, kwargs in _PRESETS[preset_name]:
        if effect_name == "gain":
            out = _apply_gain(out, kwargs["gain_db"])
        elif effect_name == "compress":
            out = _compress(out, kwargs["threshold_db"], kwargs["ratio"], kwargs.get("makeup_db", 0.0))
        elif effect_name == "lowpass":
            out = _lowpass_filter(out, sample_rate, kwargs["cutoff_hz"])
        elif effect_name == "highpass":
            out = _highpass_filter(out, sample_rate, kwargs["cutoff_hz"])
        elif effect_name == "delay":
            out = _delay(out, sample_rate, kwargs["delay_ms"], kwargs["mix"], kwargs.get("feedback", 0.0))
        elif effect_name == "reverb":
            out = _reverb(out, sample_rate, kwargs["mix"], kwargs["decay"])
        else:
            logger.warning("Skipping unknown effect step: %s", effect_name)

    return np.clip(_normalize_peak(out), -1.0, 1.0).astype(np.float32, copy=False)