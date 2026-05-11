"""Speaker embedding extraction.

Supported backends:
  - resnet34  — WeSpeaker ResNet34-LM   (256-d, wespeakerruntime, ONNX)
  - campplus  — WeSpeaker CAM++ LM      (512-d, wespeakerruntime, ONNX)
  - ecapa     — ECAPA-TDNN VoxCeleb     (192-d, ONNX Runtime)
"""

from __future__ import annotations
import os
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from .models import SpeechSegment, SubSegment

MIN_SEGMENT_DURATION: float = 0.4
EMBEDDING_WINDOW: float = 1.2
EMBEDDING_STEP: float = 0.6

_PRETRAINED = Path(
    os.environ.get("PRETRAINED_DIR")
    or Path(__file__).resolve().parent.parent / "pretrained_models"
)

# CAM++ ONNX checkpoint (downloaded from Wespeaker/wespeaker-voxceleb-campplus-LM)
CAMPP_ONNX_PATH = str(_PRETRAINED / "campplus" / "voxceleb_CAM++_LM.onnx")
# ECAPA-TDNN ONNX checkpoint (from MelissaJ/spkrec-ecapa-voxceleb-onnx)
ECAPA_ONNX_PATH = str(_PRETRAINED / "ecapa" / "ecapa_voxceleb.onnx")
# ResNet34 ONNX checkpoint — bundled locally so the packaged app does not
# trigger wespeakerruntime's first-run HuggingFace download.
RESNET34_ONNX_PATH = str(_PRETRAINED / "resnet34" / "voxceleb_resnet34_LM.onnx")

# Output dimensions per backend — used for an empty-result fallback.
_EMBED_DIMS = {"resnet34": 256, "campplus": 512, "ecapa": 192}


class _EmbeddingExtractor:
    """Uniform wrapper exposing `.extract(wav_path) -> np.ndarray` regardless
    of whether the underlying backend is wespeaker (ONNX) or SpeechBrain.

    Pour le mode live, préférer `.extract_from_array(pcm, sr)` qui évite
    disque (ECAPA: direct numpy → ONNX ; wespeaker: tempfile persistant
    réutilisé au lieu d'un nouveau fichier par extraction).
    """

    def __init__(self, embed_model: str):
        self.embed_model = embed_model
        self._persistent_tmp: str | None = None
        if embed_model == "ecapa":
            import onnxruntime as ort
            self._ort_sess = ort.InferenceSession(
                ECAPA_ONNX_PATH,
                providers=["CPUExecutionProvider"],
            )
        else:
            import wespeakerruntime as wespeaker_rt
            if embed_model == "campplus":
                self._ws = wespeaker_rt.Speaker(onnx_path=CAMPP_ONNX_PATH)
            else:  # resnet34
                # Use the bundled local ONNX rather than `lang="en"` (which
                # auto-downloads from HuggingFace on first use). Keeps the
                # packaged app fully offline.
                if Path(RESNET34_ONNX_PATH).exists():
                    self._ws = wespeaker_rt.Speaker(onnx_path=RESNET34_ONNX_PATH)
                else:
                    self._ws = wespeaker_rt.Speaker(lang="en")

    def extract(self, wav_path: str) -> np.ndarray | None:
        if self.embed_model == "ecapa":
            wav, _sr = sf.read(wav_path)
            if wav.ndim > 1:
                wav = wav.mean(axis=1)
            wav = wav.astype(np.float32)[np.newaxis, :]  # [1, time]
            emb = self._ort_sess.run(None, {"audio_input": wav})[0]
            return emb.squeeze()  # (192,)
        return self._ws.extract_embedding(wav_path)

    def extract_from_array(self, audio: np.ndarray,
                           sr: int = 16000) -> np.ndarray | None:
        """Variante in-memory (ECAPA : 100% numpy → ONNX ; wespeaker :
        tempfile persistant overwritten au lieu de create/delete à chaque
        extraction, ce qui divise par ~5 l'overhead disque sur Windows)."""
        if audio is None or audio.size == 0:
            return None
        if self.embed_model == "ecapa":
            wav = audio.astype(np.float32, copy=False)
            if wav.ndim > 1:
                wav = wav.mean(axis=1)
            wav = wav[np.newaxis, :]  # [1, time]
            emb = self._ort_sess.run(None, {"audio_input": wav})[0]
            return emb.squeeze()
        # wespeaker : la lib exige un chemin — on en réutilise un seul.
        if self._persistent_tmp is None:
            import tempfile as _tempfile
            fd, path = _tempfile.mkstemp(suffix=".wav", prefix="emb_")
            os.close(fd)
            self._persistent_tmp = path
        sf.write(self._persistent_tmp, audio, sr)
        return self._ws.extract_embedding(self._persistent_tmp)

    def __del__(self):
        if self._persistent_tmp:
            try:
                os.unlink(self._persistent_tmp)
            except OSError:
                pass


def extract_embeddings(
    audio_path: str | Path,
    speech_segments: list[SpeechSegment],
    *,
    win_len: float = EMBEDDING_WINDOW,
    hop_len: float = EMBEDDING_STEP,
    min_seg: float = MIN_SEGMENT_DURATION,
    embed_model: str = "resnet34",
) -> tuple[np.ndarray, list[SubSegment]]:
    """Extract speaker embeddings with a sliding window on each VAD segment.

    Args:
        audio_path: path to WAV (16 kHz mono recommended).
        speech_segments: VAD output.
        win_len, hop_len: sliding window length / hop in seconds.
        min_seg: skip segments shorter than this.
        embed_model: "resnet34" (256-d), "campplus" (512-d), or "ecapa" (192-d).

    Returns:
        (embeddings, subsegments) — embeddings unnormalized; normalize in clustering.
    """
    model = _EmbeddingExtractor(embed_model)

    audio, sr = sf.read(str(audio_path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    embeddings: list[np.ndarray] = []
    subsegments: list[SubSegment] = []

    for idx, seg in enumerate(speech_segments):
        if seg.duration < min_seg:
            continue

        if seg.duration <= win_len * 1.5:
            windows = [(seg.start, seg.end)]
        else:
            windows = []
            ws = seg.start
            while ws + min_seg < seg.end:
                we = min(ws + win_len, seg.end)
                windows.append((ws, we))
                ws += hop_len

        for ws, we in windows:
            s_sample = int(ws * sr)
            e_sample = int(we * sr)
            chunk = audio[s_sample:e_sample]

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                    sf.write(tmp_path, chunk, sr)
                emb = model.extract(tmp_path)
            except Exception:
                continue
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

            if emb is not None:
                if emb.ndim == 2:
                    emb = emb[0]
                embeddings.append(emb)
                subsegments.append(SubSegment(start=ws, end=we, parent_idx=idx))

    if not embeddings:
        dim = _EMBED_DIMS.get(embed_model, 256)
        return np.empty((0, dim), dtype=np.float32), []

    return np.stack(embeddings), subsegments
