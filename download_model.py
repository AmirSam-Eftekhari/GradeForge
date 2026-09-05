#!/usr/bin/env python3
"""
One-time helper: download a semantic embedding model to a local folder so
GradeForge (or the CLI) can load it with *zero* network access afterward.

Run this ONCE, on any machine that has internet access:

    pip install sentence-transformers torch
    python download_model.py --model intfloat/multilingual-e5-large

Then copy the output folder (by default ./models/multilingual-e5-large)
to the offline machine, and either:

  - paste its path into Settings -> AI -> Model in the desktop app, or
  - pass it as --model to main.py's embedding config.

GradeForge detects a local folder automatically (src/ai/embedding_backend.py
-- SentenceTransformerBackend checks Path(model_name).exists()) and sets
HF_HUB_OFFLINE=1 / TRANSFORMERS_OFFLINE=1 for that load, so it never makes
a network call once you're pointed at a local folder -- not even to check
for a newer revision of an already-cached model.

Recommended models (multilingual, no translation step needed):
    intfloat/multilingual-e5-large   (~2.2GB, spec's default)
    BAAI/bge-m3                       (~2.3GB, strong alternative)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="intfloat/multilingual-e5-large", help="HuggingFace model ID to download")
    parser.add_argument("--out", default=None, help="Output folder (default: models/<model-name>)")
    args = parser.parse_args()

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("sentence-transformers isn't installed here. Run:\n    pip install sentence-transformers torch", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else Path("models") / args.model.split("/")[-1]
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading '{args.model}' (needs internet access, one time only)...")
    model = SentenceTransformer(args.model)
    model.save(str(out_dir))

    print(f"\nSaved to: {out_dir.resolve()}")
    print("Copy this folder to the offline machine, then set it as the Model")
    print("field in Settings -> AI. No internet is needed after that.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
