#!/usr/bin/env python3
"""
Objective audio quality checks for Vuclear outputs.

Usage:
    python tests/eval/run_checks.py --output path/to/output.wav [--script "original text"]

Or run the full test matrix:
    python tests/eval/run_checks.py --full-matrix
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def check_format_validity(wav_path: Path, mp3_path: Path | None = None) -> dict:
    """Verify WAV and MP3 headers with ffprobe."""
    results = {}

    def probe(path: Path) -> bool:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
            capture_output=True, text=True,
        )
        return result.returncode == 0

    results["wav_valid"] = probe(wav_path)
    if mp3_path and mp3_path.exists():
        results["mp3_valid"] = probe(mp3_path)
    return results


def check_audio(wav_path: Path) -> dict:
    """Run all numeric checks on a WAV file."""
    import numpy as np
    import librosa
    import pyloudnorm as pyln
    import soundfile as sf

    audio, sr = sf.read(str(wav_path), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    duration = len(audio) / sr
    peak = float(np.max(np.abs(audio)))

    # Loudness
    meter = pyln.Meter(sr)
    loudness = float(meter.integrated_loudness(audio))

    # Leading/trailing silence check (first and last 100ms)
    margin = int(0.1 * sr)
    has_content_start = np.max(np.abs(audio[:margin])) > 0.01
    has_content_end = np.max(np.abs(audio[-margin:])) > 0.01

    # Leading silence duration
    non_silent = np.where(np.abs(audio) > 0.01)[0]
    leading_silence_s = float(non_silent[0] / sr) if len(non_silent) > 0 else duration
    trailing_silence_s = float((len(audio) - non_silent[-1]) / sr) if len(non_silent) > 0 else duration

    return {
        "duration_s": round(duration, 2),
        "sample_rate": sr,
        "peak": round(peak, 4),
        "loudness_lufs": round(loudness, 1) if not (loudness != loudness) else None,  # NaN check
        "no_clipping": peak < 0.99,
        "loudness_in_range": -16.0 <= loudness <= -12.0 if loudness == loudness else False,
        "leading_silence_s": round(leading_silence_s, 2),
        "trailing_silence_s": round(trailing_silence_s, 2),
        "no_excess_leading_silence": leading_silence_s < 1.0,
        "no_excess_trailing_silence": trailing_silence_s < 1.0,
    }


def estimate_expected_duration(text: str, speed: float = 1.0) -> float:
    """Rough estimate: ~130 words/min at speed=1.0."""
    words = len(text.split())
    mins = words / 130 / speed
    return mins * 60


def print_report(checks: dict, label: str = "") -> bool:
    """Print formatted report. Returns True if all pass."""
    all_pass = True
    label_str = f" [{label}]" if label else ""
    print(f"\n{'='*60}")
    print(f"Audio Quality Report{label_str}")
    print("="*60)

    PASS_CHECKS = [
        "wav_valid", "mp3_valid", "no_clipping",
        "loudness_in_range", "no_excess_leading_silence", "no_excess_trailing_silence",
    ]
    INFO_KEYS = [
        "duration_s", "sample_rate", "peak", "loudness_lufs",
        "leading_silence_s", "trailing_silence_s",
    ]

    for key in INFO_KEYS:
        if key in checks:
            print(f"  {key}: {checks[key]}")

    print()
    for key in PASS_CHECKS:
        if key in checks:
            val = checks[key]
            symbol = "✓" if val else "✗"
            status = "PASS" if val else "FAIL"
            print(f"  {symbol} {key}: {status}")
            if not val:
                all_pass = False

    print()
    print(f"  Overall: {'ALL PASS ✓' if all_pass else 'FAILURES DETECTED ✗'}")
    return all_pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice output quality checker")
    parser.add_argument("--output", type=Path, help="WAV file to check")
    parser.add_argument("--mp3", type=Path, help="MP3 file to check")
    parser.add_argument("--script", help="Original script (for duration accuracy estimate)")
    parser.add_argument("--full-matrix", action="store_true", help="Run on all outputs in ./data/outputs/")
    parser.add_argument("--results-json", type=Path, help="Write results to JSON file")
    args = parser.parse_args()

    all_results = {}

    if args.full_matrix:
        outputs_dir = Path("data/outputs")
        wav_files = list(outputs_dir.glob("*/output.wav"))
        if not wav_files:
            print("No output WAV files found in data/outputs/")
            sys.exit(0)
        print(f"Found {len(wav_files)} output(s) to check…")
        all_pass = True
        for wav in wav_files:
            mp3 = wav.parent / "output.mp3"
            checks = {}
            checks.update(check_format_validity(wav, mp3 if mp3.exists() else None))
            checks.update(check_audio(wav))
            output_id = wav.parent.name
            all_results[output_id] = checks
            passed = print_report(checks, label=output_id[:8])
            all_pass = all_pass and passed

        if args.results_json:
            args.results_json.write_text(json.dumps(all_results, indent=2))
            print(f"\nResults written to {args.results_json}")

        sys.exit(0 if all_pass else 1)

    if not args.output:
        parser.error("Provide --output or --full-matrix")

    if not args.output.exists():
        print(f"ERROR: File not found: {args.output}")
        sys.exit(1)

    checks = {}
    checks.update(check_format_validity(args.output, args.mp3))
    checks.update(check_audio(args.output))

    if args.script:
        expected = estimate_expected_duration(args.script)
        actual = checks.get("duration_s", 0)
        tolerance = 0.20
        duration_ok = abs(actual - expected) / max(expected, 1) <= tolerance
        checks["duration_accuracy"] = duration_ok
        checks["expected_duration_s"] = round(expected, 1)
        print(f"  Expected duration: ~{expected:.1f}s | Actual: {actual:.1f}s")

    all_results["check"] = checks
    passed = print_report(checks)

    if args.results_json:
        args.results_json.write_text(json.dumps(all_results, indent=2))

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
