import os as _os
# MUST run before numpy/scipy are imported anywhere in the package.
# Multithreaded BLAS makes ARPACK/eigh non-deterministic -> NMESC speaker
# count flips (e.g. k=1 instead of k=5 on identical audio).
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
           "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

"""Speaker diarization + transcription pipeline (transcribe-first).

Pipeline order:
  1. Audio conversion (16kHz mono WAV)
  2. ASR on full audio → words with timestamps
  3. VAD + Embeddings + Clustering → diarization segments
  4. Align words to speakers

Modules:
  - audio.py       : audio conversion + duration
  - models.py      : data structures (Segment, SpeechSegment, ...)
  - vad.py         : Silero VAD
  - embeddings.py  : WeSpeaker ResNet34-LM (ONNX)
  - clustering.py  : NME-SC, Spectral (+enhance)
  - refinement.py  : VBx (Variational Bayes HMM)
  - segments.py    : assemble + write RTTM/TXT
  - transcription.py : sherpa-onnx streaming Zipformer (FR)
  - tracking.py    : MLflow tracking
  - run.py         : CLI orchestrator
"""

from .models import Segment, SpeechSegment, SubSegment, SpeakerEstimationDetails
from .audio import convert_to_wav, get_audio_duration
from .vad import run_vad
from .embeddings import extract_embeddings, EMBEDDING_WINDOW, EMBEDDING_STEP
from .clustering import (
    estimate_speakers_nmesc,
    cluster_sc,
    cluster_speakers,
    sim_enhancement,
)
from .refinement import refine_vbx
from .segments import build_segments, write_rttm, write_txt
from .transcription import transcribe, align_words_to_speakers, words_to_turns

__all__ = [
    "Segment", "SpeechSegment", "SubSegment", "SpeakerEstimationDetails",
    "convert_to_wav", "get_audio_duration",
    "run_vad",
    "extract_embeddings", "EMBEDDING_WINDOW", "EMBEDDING_STEP",
    "estimate_speakers_nmesc",
    "cluster_sc", "cluster_speakers",
    "sim_enhancement",
    "refine_vbx",
    "build_segments", "write_rttm", "write_txt",
    "transcribe", "align_words_to_speakers", "words_to_turns",
]
