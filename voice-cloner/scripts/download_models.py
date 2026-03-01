#!/usr/bin/env python3
"""
Download and verify model weights for voice-cloner.

Usage:
    python scripts/download_models.py [--engine chatterbox|metavoice|f5_noncommercial]
"""
import argparse
import sys
import textwrap

LICENSE_NOTICES = {
    "chatterbox": textwrap.dedent("""
        ╔══════════════════════════════════════════════════════════════╗
        ║  Chatterbox TTS — MIT License                               ║
        ║                                                              ║
        ║  Model weights:  MIT                                         ║
        ║  Commercial use: YES                                         ║
        ║  Source: https://github.com/resemble-ai/chatterbox           ║
        ║                                                              ║
        ║  Note: Outputs include a built-in Perth perceptual           ║
        ║  watermark for content authenticity.                         ║
        ╚══════════════════════════════════════════════════════════════╝
    """),
    "metavoice": textwrap.dedent("""
        ╔══════════════════════════════════════════════════════════════╗
        ║  MetaVoice-1B — Apache 2.0 License                          ║
        ║                                                              ║
        ║  Model weights:  Apache 2.0                                  ║
        ║  Commercial use: YES                                         ║
        ║  Source: https://github.com/metavoiceio/metavoice-src        ║
        ║                                                              ║
        ║  Requirements: 10–12GB VRAM (RTX 3080+)                     ║
        ╚══════════════════════════════════════════════════════════════╝
    """),
    "f5_noncommercial": textwrap.dedent("""
        ╔══════════════════════════════════════════════════════════════╗
        ║  F5-TTS — CC-BY-NC-4.0 (NON-COMMERCIAL ONLY)               ║
        ║                                                              ║
        ║  Model weights:  CC-BY-NC-4.0                               ║
        ║  Commercial use: NO — prohibited by license                  ║
        ║  Source: https://huggingface.co/SWivid/F5-TTS               ║
        ║                                                              ║
        ║  ⚠️  Do NOT use in any commercial product or paid service.   ║
        ║  For commercial use, select: chatterbox or metavoice         ║
        ╚══════════════════════════════════════════════════════════════╝
    """),
}


def download_chatterbox() -> None:
    print("Downloading Chatterbox weights via HuggingFace Hub…")
    try:
        from chatterbox.tts import ChatterboxTTS
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"  Using device: {device}")
        model = ChatterboxTTS.from_pretrained(device=device)
        print("  Chatterbox loaded successfully.")
        del model
    except ImportError:
        print("\nERROR: chatterbox-tts not installed.")
        print("Run: pip install chatterbox-tts")
        print("Or:  pip install git+https://github.com/resemble-ai/chatterbox.git")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR downloading Chatterbox: {e}")
        sys.exit(1)


def download_metavoice() -> None:
    print("Downloading MetaVoice-1B weights…")
    try:
        from fam.llm.fast_inference import TTS
        tts = TTS()
        print("  MetaVoice-1B loaded successfully.")
        del tts
    except ImportError:
        print("\nERROR: MetaVoice not installed.")
        print("Run: pip install git+https://github.com/metavoiceio/metavoice-src.git")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR downloading MetaVoice: {e}")
        sys.exit(1)


def download_f5tts() -> None:
    print("Downloading F5-TTS weights (CC-BY-NC-4.0)…")
    try:
        from f5_tts.api import F5TTS
        model = F5TTS()
        print("  F5-TTS loaded successfully.")
        del model
    except ImportError:
        print("\nERROR: f5-tts not installed.")
        print("Run: pip install f5-tts")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR downloading F5-TTS: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download voice model weights")
    parser.add_argument(
        "--engine",
        choices=["chatterbox", "metavoice", "f5_noncommercial"],
        default="chatterbox",
    )
    args = parser.parse_args()

    engine = args.engine
    print(LICENSE_NOTICES[engine])

    if engine == "f5_noncommercial":
        print("⚠️  Type 'yes' to confirm you accept CC-BY-NC-4.0 (non-commercial only): ", end="")
        if input().strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    if engine == "chatterbox":
        download_chatterbox()
    elif engine == "metavoice":
        download_metavoice()
    elif engine == "f5_noncommercial":
        download_f5tts()

    print(f"\nModel '{engine}' ready. Set VOICE_ENGINE={engine} in .env to use it.")


if __name__ == "__main__":
    main()
