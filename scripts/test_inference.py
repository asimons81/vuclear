#!/usr/bin/env python3
"""
CLI test for the voice synthesis pipeline.

Usage:
    python scripts/test_inference.py \
        --ref sample.wav \
        --text "Hello, this is a test of voice cloning." \
        [--engine chatterbox] \
        [--speed 1.0] \
        [--output out.wav]
"""
import argparse
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Test voice synthesis pipeline")
    parser.add_argument("--ref", required=True, type=Path, help="Reference WAV file (16kHz mono)")
    parser.add_argument("--text", required=True, help="Text to synthesize")
    parser.add_argument("--engine", default=None, help="Override VOICE_ENGINE env var")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (0.7–1.3)")
    parser.add_argument("--output", type=Path, default=Path("test_output.wav"))
    parser.add_argument("--no-preprocess", action="store_true", help="Skip reference preprocessing")
    args = parser.parse_args()

    if not args.ref.exists():
        print(f"ERROR: Reference file not found: {args.ref}")
        sys.exit(1)

    # Set engine override before importing config
    if args.engine:
        import os
        os.environ["VOICE_ENGINE"] = args.engine

    print(f"Engine: {args.engine or 'from VOICE_ENGINE env'}")
    print(f"Reference: {args.ref}")
    print(f"Text ({len(args.text)} chars): {args.text[:80]}{'…' if len(args.text) > 80 else ''}")
    print(f"Speed: {args.speed}x")
    print()

    # Preprocess reference if needed
    ref_path = args.ref
    if not args.no_preprocess:
        import tempfile
        from backend.services.audio_pipeline import preprocess_reference

        print("Preprocessing reference audio…")
        t0 = time.time()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            processed_path = Path(tmp.name)
        duration = preprocess_reference(args.ref, processed_path)
        print(f"  Done in {time.time()-t0:.2f}s → {duration:.1f}s of clean audio\n")
        ref_path = processed_path

    # Load model
    from backend.services.model.factory import get_model
    print("Loading model…")
    t0 = time.time()
    model = get_model()
    print(f"  {model.ENGINE_NAME} loaded in {time.time()-t0:.2f}s")
    print(f"  License: {model.LICENSE} | Commercial: {'YES' if model.COMMERCIAL_OK else 'NO (non-commercial only)'}\n")

    # Synthesize
    print("Synthesizing…")
    t0 = time.time()
    audio = model.synthesize(text=args.text, reference_wav=ref_path, speed=args.speed)
    elapsed = time.time() - t0
    duration = len(audio) / model.SAMPLE_RATE
    rtf = elapsed / duration if duration > 0 else float("inf")
    print(f"  Done in {elapsed:.2f}s → {duration:.1f}s audio (RTF: {rtf:.2f}x)\n")

    # Post-process and export
    import numpy as np
    import soundfile as sf
    import librosa
    import pyloudnorm as pyln

    TARGET_SR = 44100
    TARGET_LUFS = -14.0

    if model.SAMPLE_RATE != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=model.SAMPLE_RATE, target_sr=TARGET_SR)

    meter = pyln.Meter(TARGET_SR)
    loudness = meter.integrated_loudness(audio)
    if not np.isinf(loudness):
        audio = pyln.normalize.loudness(audio, loudness, TARGET_LUFS)
    audio = np.clip(audio, -0.99, 0.99)

    sf.write(str(args.output), audio, TARGET_SR, subtype="PCM_24")
    print(f"Output saved: {args.output}")
    print(f"Peak: {np.max(np.abs(audio)):.3f} | Loudness: {loudness:.1f} LUFS")

    # Cleanup
    if not args.no_preprocess and ref_path != args.ref:
        ref_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
