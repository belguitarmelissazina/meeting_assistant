"""Pre-warm local ML models for the offline installer.

The packaged Meeting Assistant must run fully offline. sentence-transformers
`all-MiniLM-L6-v2` (~80 MB) is used by meeting_minutes_pipeline.py for
semantic boundary detection.

We download the model as REAL FILES (no symlinks) into
    assets/models_hf/all-MiniLM-L6-v2/
Symlinks are avoided because:
  - HuggingFace's default cache uses symlinks from snapshots/ → blobs/
  - On Windows (especially inside OneDrive), 7-Zip / electron-builder fails
    to pack those reparse points → "Nom de répertoire non valide" errors.

At runtime meeting_minutes_pipeline.py reads the MINILM_DIR env var (set by
Electron) and passes that absolute path to SentenceTransformer, so no HF
lookup is required.

Usage:
    python scripts/prepare_assets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_HF_DIR = PROJECT_ROOT / "assets" / "models_hf"
MINILM_DIR = MODELS_HF_DIR / "all-MiniLM-L6-v2"


def main() -> None:
    MODELS_HF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[prepare_assets] Downloading all-MiniLM-L6-v2 → {MINILM_DIR}")

    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id="sentence-transformers/all-MiniLM-L6-v2",
        local_dir=str(MINILM_DIR),
        local_dir_use_symlinks=False,
        allow_patterns=[
            "config.json",
            "config_sentence_transformers.json",
            "modules.json",
            "sentence_bert_config.json",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.txt",
            "model.safetensors",
            "1_Pooling/*",
            "2_Normalize/*",
        ],
    )

    print("[prepare_assets] Smoke-testing the local copy...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(str(MINILM_DIR), device="cpu")
    _ = model.encode(["bonjour"], convert_to_numpy=True)
    print("[prepare_assets] done.")
    print()
    print("Contents:")
    for p in sorted(MINILM_DIR.rglob("*")):
        if p.is_file():
            sz = p.stat().st_size / (1024 * 1024)
            print(f"  {sz:6.1f} MB  {p.relative_to(MINILM_DIR)}")


if __name__ == "__main__":
    sys.exit(main() or 0)
