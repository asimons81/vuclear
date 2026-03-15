#!/usr/bin/env python3
"""
WER (Word Error Rate) proxy evaluation using Whisper transcription.

Requires: pip install openai-whisper jiwer

Usage:
    python tests/eval/run_wer.py --output path/to/output.wav --script "original text"
    python tests/eval/run_wer.py --full-matrix  # runs on all data/outputs/
"""
import argparse
import json
import sys
from pathlib import Path


def transcribe(wav_path: Path, model_size: str = "tiny") -> str:
    try:
        import whisper
    except ImportError:
        print("ERROR: openai-whisper not installed. Run: pip install openai-whisper")
        sys.exit(1)

    print(f"  Transcribing {wav_path.name} with Whisper ({model_size})…", end="", flush=True)
    model = whisper.load_model(model_size)
    result = model.transcribe(str(wav_path))
    text = result["text"].strip()
    print(f" done.")
    return text


def compute_wer(reference: str, hypothesis: str) -> float:
    try:
        from jiwer import wer
        return float(wer(reference, hypothesis))
    except ImportError:
        print("ERROR: jiwer not installed. Run: pip install jiwer")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="WER evaluation for voice outputs")
    parser.add_argument("--output", type=Path, help="WAV output file")
    parser.add_argument("--script", help="Original script text")
    parser.add_argument("--whisper-model", default="tiny", choices=["tiny", "base", "small", "medium"])
    parser.add_argument("--full-matrix", action="store_true", help="Run on all outputs with meta.json")
    parser.add_argument("--results-json", type=Path, default=Path("tests/eval/wer_results.json"))
    parser.add_argument("--target-wer", type=float, default=0.05, help="Pass threshold (default 5%%)")
    args = parser.parse_args()

    results = {}

    if args.full_matrix:
        outputs_dir = Path("data/outputs")
        meta_files = list(outputs_dir.glob("*/meta.json"))
        if not meta_files:
            print("No outputs with meta.json found.")
            sys.exit(0)

        print(f"Evaluating {len(meta_files)} output(s)…\n")
        all_pass = True

        for meta_path in meta_files:
            output_id = meta_path.parent.name
            wav_path = meta_path.parent / "output.wav"
            if not wav_path.exists():
                continue

            meta = json.loads(meta_path.read_text())
            script = meta.get("script", "")

            hypothesis = transcribe(wav_path, args.whisper_model)
            wer_val = compute_wer(script, hypothesis)
            passed = wer_val <= args.target_wer

            results[output_id] = {
                "reference": script[:200],
                "hypothesis": hypothesis[:200],
                "wer": round(wer_val, 4),
                "passed": passed,
            }

            symbol = "✓" if passed else "✗"
            print(f"  {symbol} {output_id[:8]}: WER={wer_val:.1%} {'PASS' if passed else 'FAIL'}")
            if not passed:
                all_pass = False

        args.results_json.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to {args.results_json}")
        sys.exit(0 if all_pass else 1)

    if not args.output or not args.script:
        parser.error("Provide --output and --script, or use --full-matrix")

    if not args.output.exists():
        print(f"ERROR: {args.output} not found")
        sys.exit(1)

    hypothesis = transcribe(args.output, args.whisper_model)
    wer_val = compute_wer(args.script, hypothesis)
    passed = wer_val <= args.target_wer

    print(f"\nReference:  {args.script[:120]}")
    print(f"Hypothesis: {hypothesis[:120]}")
    print(f"WER:        {wer_val:.1%} {'✓ PASS' if passed else '✗ FAIL'} (target ≤{args.target_wer:.0%})")

    results["result"] = {"wer": round(wer_val, 4), "passed": passed}
    args.results_json.write_text(json.dumps(results, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
