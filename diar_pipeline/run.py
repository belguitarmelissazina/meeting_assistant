#!/usr/bin/env python3
"""Transcribe-first diarization pipeline.

Pipeline order:
  1. Audio conversion (16kHz mono WAV)
  2. ASR on full audio -> words with timestamps
  3. VAD + Embeddings + Clustering -> diarization segments
  4. Align words to speakers

Usage:
  python -m diar_pipeline.run -i meeting.wav
  python -m diar_pipeline.run -i meeting.wav --num-speakers 3
"""

from __future__ import annotations
import os as _os
# Force single-threaded BLAS BEFORE numpy/scipy import — otherwise ARPACK /
# eigh results vary run-to-run under multithreaded MKL/OpenBLAS, which caused
# NMESC speaker-count flips (k=1 instead of k=N) and DER swings on identical
# inputs. MUST be set before numpy/scipy are imported anywhere.
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
           "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import argparse
import sys
import time
from pathlib import Path

from .audio import convert_to_wav, get_audio_duration
from .vad import run_vad
from .embeddings import extract_embeddings
from .clustering import cluster_speakers, cluster_speakers_bootstrap_online
from .segments import build_segments, write_rttm, write_txt


# ── Fixed config ────────────────────────────────────────────────────────────
EMBED_MODEL = "resnet34"
ESTIMATE_METHOD = "nmesc"
CLUSTER_METHOD = "sc"
ENHANCE = True
WIN_LEN = 1.2
HOP_LEN = 0.6
VAD_MODEL = "silero"
VAD_THRESHOLD = 0.4
VAD_MIN_SPEECH_MS = 200
VAD_MIN_SILENCE_MS = 50
VAD_PAD_MS = 20


def main() -> None:
    ap = argparse.ArgumentParser(description="Diarization + transcription pipeline")
    ap.add_argument("--input", "-i", required=True, help="Audio file path")
    ap.add_argument("--output-dir", "-o", default=None, help="Output directory")
    ap.add_argument("--num-speakers", type=int, default=None,
                    help="Force number of speakers (auto-detect if omitted)")
    ap.add_argument("--no-diarize", action="store_true",
                    help="Skip diarization : transcribe only, one speaker")
    ap.add_argument("--bootstrap-online", action="store_true",
                    help="Clustering bootstrap + online (NMESC sur les 10 premières "
                         "min, puis assignation online pour la suite). Utile pour "
                         "le mode 'live' : pas besoin de la vue globale pour assigner.")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERROR: {in_path} not found")
        sys.exit(1)

    file_id = in_path.stem
    out_dir = (Path(args.output_dir) if args.output_dir
               else Path(__file__).resolve().parent.parent / "outputs" / file_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"  DIARISATION + TRANSCRIPTION — {in_path.name}")
    print("=" * 60)

    t_pipeline = time.perf_counter()

    # ── 1. Audio ────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    wav_path = convert_to_wav(in_path)
    duration = get_audio_duration(str(wav_path))
    print(f"  [1] audio -> {wav_path.name} ({duration:.1f}s)  "
          f"{time.perf_counter() - t0:.1f}s")

    # ── 2. Transcription ────────────────────────────────────────────────
    from .transcription import (
        load_audio_pcm, transcribe as run_asr,
        align_words_to_speakers, align_words_by_boundaries,
        words_to_turns, format_transcript_txt,
        DEFAULT_MODEL_DIR,
    )
    t_asr = time.perf_counter()
    print(f"  [2] Transcription (sherpa-onnx)...")
    audio_pcm = load_audio_pcm(in_path)
    words = run_asr(audio_pcm, model_dir=DEFAULT_MODEL_DIR)
    print(f"      -> {len(words)} words  {time.perf_counter() - t_asr:.1f}s")

    # ── No-diarize shortcut ─────────────────────────────────────────────
    if args.no_diarize:
        for w in words:
            w["speaker"] = "SPEAKER_00"
        turns = words_to_turns(words)
        import json as _json
        (out_dir / f"{file_id}.words_midpoint.json").write_text(
            _json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / f"{file_id}.turns_midpoint.json").write_text(
            _json.dumps(turns, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / f"{file_id}.words.json").write_text(
            _json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / f"{file_id}.turns.json").write_text(
            _json.dumps(turns, ensure_ascii=False, indent=2), encoding="utf-8")
        txt = format_transcript_txt(turns, with_timestamps=True)
        (out_dir / f"{file_id}.transcript.midpoint.txt").write_text(txt, encoding="utf-8")
        total = time.perf_counter() - t_pipeline
        print()
        print("=" * 60)
        print(f"  DONE (no diarization)")
        print("=" * 60)
        print(f"  Duration  : {duration:.1f}s ({duration/60:.1f} min)")
        print(f"  Words     : {len(words)}")
        print(f"  Time      : {total:.1f}s (RTF {total/duration:.2f}x)")
        print(f"  Output    : {out_dir}")
        print()
        return

    # ── 3. VAD ──────────────────────────────────────────────────────────
    t1 = time.perf_counter()
    speech_segments = run_vad(
        str(wav_path),
        model=VAD_MODEL,
        threshold=VAD_THRESHOLD,
        min_speech_duration_ms=VAD_MIN_SPEECH_MS,
        min_silence_duration_ms=VAD_MIN_SILENCE_MS,
        speech_pad_ms=VAD_PAD_MS,
    )
    print(f"  [3] VAD: {len(speech_segments)} segments  "
          f"{time.perf_counter() - t1:.1f}s")
    if not speech_segments:
        print("  ERROR: no speech detected")
        sys.exit(1)

    # ── 4. Embeddings ───────────────────────────────────────────────────
    t2 = time.perf_counter()
    embeddings, subsegments = extract_embeddings(
        str(wav_path), speech_segments,
        win_len=WIN_LEN, hop_len=HOP_LEN, embed_model=EMBED_MODEL)
    print(f"  [4] Embeddings: {embeddings.shape[0]} x {embeddings.shape[1]}  "
          f"{time.perf_counter() - t2:.1f}s")

    # ── 5. Clustering ───────────────────────────────────────────────────
    t3 = time.perf_counter()
    if args.bootstrap_online:
        # HOP_LEN = 0.6s → ~1000 embeddings pour 10 min. On prend ce nombre
        # en plancher dynamique (au cas où HOP_LEN change).
        bootstrap_size = max(200, int(10 * 60 / HOP_LEN))
        labels, details = cluster_speakers_bootstrap_online(
            embeddings,
            bootstrap_size=bootstrap_size,
            num_speakers_bootstrap=args.num_speakers,
        )
    else:
        labels, details = cluster_speakers(
            embeddings,
            num_speakers=args.num_speakers,
            method=CLUSTER_METHOD,
            enhance=ENHANCE,
            estimate_method=ESTIMATE_METHOD,
        )
    n_spk = len(set(labels.tolist()))
    mode = "bootstrap+online" if args.bootstrap_online else "batch"
    print(f"  [5] Clustering ({mode}): {n_spk} speakers  "
          f"{time.perf_counter() - t3:.1f}s")

    # ── 6. Build segments ───────────────────────────────────────────────
    segments = build_segments(speech_segments, subsegments, labels)
    rttm_path = out_dir / f"{file_id}.rttm"
    txt_path = out_dir / f"{file_id}.diarization.txt"
    write_rttm(rttm_path, segments, file_id)
    write_txt(txt_path, segments)

    # ── 7. Align words to speakers ──────────────────────────────────────
    print(f"  [6] Aligning {len(words)} words to {n_spk} speakers...")

    words_mid = align_words_to_speakers([dict(w) for w in words], segments)
    turns_mid = words_to_turns(words_mid)

    words_bnd = align_words_by_boundaries(words, segments, hop_seconds=5.0)
    turns_bnd = words_to_turns(words_bnd)

    # Save per-word + per-turn JSON (exact logic from diarisation+transcription)
    import json as _json
    (out_dir / f"{file_id}.words_midpoint.json").write_text(
        _json.dumps(words_mid, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{file_id}.turns_midpoint.json").write_text(
        _json.dumps(turns_mid, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{file_id}.words_boundary.json").write_text(
        _json.dumps(words_bnd, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{file_id}.turns_boundary.json").write_text(
        _json.dumps(turns_bnd, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{file_id}.words.json").write_text(
        _json.dumps(words_mid, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{file_id}.turns.json").write_text(
        _json.dumps(turns_mid, ensure_ascii=False, indent=2), encoding="utf-8")

    spk_counts: dict[str, int] = {}
    for w in words_mid:
        spk_counts[w["speaker"]] = spk_counts.get(w["speaker"], 0) + 1
    (out_dir / f"{file_id}.words_per_speaker.json").write_text(
        _json.dumps(spk_counts, ensure_ascii=False, indent=2), encoding="utf-8")

    for label, turns in (("midpoint", turns_mid), ("boundary", turns_bnd)):
        txt = format_transcript_txt(turns, with_timestamps=True)
        p = out_dir / f"{file_id}.transcript.{label}.txt"
        p.write_text(txt, encoding="utf-8")

    print(f"      midpoint: {len(turns_mid)} turns | "
          f"boundary: {len(turns_bnd)} turns | "
          f"speakers: {spk_counts}")

    total = time.perf_counter() - t_pipeline

    print()
    print("=" * 60)
    print(f"  DONE")
    print("=" * 60)
    print(f"  Duration  : {duration:.1f}s ({duration/60:.1f} min)")
    print(f"  Speakers  : {n_spk}")
    print(f"  Words     : {len(words)}")
    print(f"  Time      : {total:.1f}s (RTF {total/duration:.2f}x)")
    print(f"  Output    : {out_dir}")
    print()


if __name__ == "__main__":
    main()
