"""
Pipeline final — Compte rendu de réunion
==========================================
Topic Boundary Detection + Assemblage déterministe (fusion v3 + v4).

Architecture :
  Segments → Fenêtres glissantes → Embeddings → Similarités consécutives
  → Détection de vallées (percentile) → Chunks thématiques
  → LLM (résumé + extraction par chunk) → Executive summary
  → Recommandations → Assemblage Markdown déterministe

Artefacts sauvegardés dans results/meeting_minutes/<transcript>/<model>/<mode>/ :
  - compte_rendu.md
  - compte_rendu.sections.json     (JSON structuré par chunk, cache)
  - compte_rendu.assembly.json     (données intermédiaires d'assemblage)
  - compte_rendu.metrics.json
  - compte_rendu.similarity.json / .png
"""

import atexit
import json
import os
import re
import subprocess
import sys
import threading
import time
import logging
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import psutil
from scipy.ndimage import gaussian_filter1d
from sentence_transformers import SentenceTransformer

# Force stdout/stderr en UTF-8 sur Windows (console PowerShell defaut cp1252
# qui ne sait pas encoder les caracteres unicode genre ->, ↳, etc.).
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Charge automatiquement .env (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mesure RAM / temps
# ---------------------------------------------------------------------------
_proc = psutil.Process()

def ram_mb() -> float:
    return _proc.memory_info().rss / 1024 / 1024

def ram_total_mb() -> float:
    return (psutil.virtual_memory().total - psutil.virtual_memory().available) / 1024 / 1024

def log_perf(label: str, t0: float) -> None:
    elapsed = time.time() - t0
    log.info(f"[PERF] {label:<40} {elapsed:6.1f}s | RAM py={ram_mb():.0f} Mo | RAM sys={ram_total_mb():.0f} Mo")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class Config:
    # ── Source ──
    json_path: str = "result_diarize_sherpa.json"
    transcript_path: str = "transcript1.txt"  # prioritaire sur json_path

    # ── Embeddings ──
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 32

    # ── Topic boundary detection ──
    # Taille de la fenêtre glissante pour calculer les embeddings
    boundary_window_size: int = 3
    # Sigma du lissage gaussien sur la courbe de similarité
    boundary_smoothing_sigma: float = 2.0
    # Percentile des similarités en dessous duquel on considère une frontière
    # Plus bas = moins de coupures (chunks plus gros)
    boundary_percentile: float = 5.0
    # Distance minimum (en nombre de fenêtres) entre deux frontières
    boundary_min_distance: int = 10
    # Taille max d'un chunk (chars) — si dépassé, re-split sémantique récursif
    max_chunk_chars: int = 15000

    # ── llama-server.exe ──
    # Packaged builds override these via env vars (LLAMA_BIN_DIR, MODELS_DIR)
    # so the bundled `bin/llama/` and `models/` can live outside the project tree.
    llama_server_exe: str = str(
        Path(os.environ.get("LLAMA_BIN_DIR")
             or Path(__file__).parent / "bin" / "llama")
        / "llama-server.exe"
    )
    llm_model_path: str = str(
        Path(os.environ.get("MODELS_DIR")
             or Path(__file__).parent / "models")
        / "mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"
    )
    llm_n_ctx: int = 0
    llm_n_threads: int = 6
    llm_n_gpu_layers: int = 0
    llm_temperature: float = 0.2
    llm_repeat_penalty: float = 1.1
    llm_kv_cache_type: str = "q8_0"
    llm_server_host: str = "127.0.0.1"
    llm_server_port: int = 8765
    llm_server_startup_timeout: int = 86400
    llm_section_timeout: int = 86400

    # ── Prompts ──
    # True  → utilise les PROMPT_*_SMALL (prompts compacts, pour modèles <3B)
    # False → utilise les PROMPT_* originaux (testés sur Mistral-3B)
    small_model: bool = False

    # ── Plan d'attaque ──
    # "perchunk" : plan unifié (engagement + suggestion, cap 2 items/chunk via
    #              grammar) extrait par chunk pendant la réunion (1 appel LLM
    #              en plus par chunk, HIT cache sur [system][chunk]). Plan
    #              final = assemblage déterministe.
    # "legacy"   : 1 appel LLM final sur les résumés agrégés. Pas de hit cache.
    # Override via env var MEETING_PLAN_MODE.
    plan_attack_mode: str = field(
        default_factory=lambda: os.environ.get("MEETING_PLAN_MODE", "perchunk")
    )

    # ── Sortie ──
    output_path: str = "compte_rendu.md"


# ---------------------------------------------------------------------------
# Étape 0 : Chargement
# ---------------------------------------------------------------------------
def load_segments(json_path: str) -> list[dict]:
    log.info(f"Chargement JSON : {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    segments = data.get("segments", [])
    segments.sort(key=lambda s: s.get("start", 0))
    log.info(f"{len(segments)} segments chargés.")
    return segments


def load_segments_from_transcript(txt_path: str) -> list[dict]:
    """Parse transcript avec ou sans timestamps."""
    log.info(f"Chargement transcript : {txt_path}")
    re_with_ts = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\]\s+(.+?):\s+(.*)")
    re_with_ts_short = re.compile(r"^\[(\d{2}):(\d{2})\]\s+\*{0,2}(.+?)\*{0,2}:\s+(.*)")
    re_with_ts_range = re.compile(
        r"^\[(\d{2}):(\d{2}(?:\.\d+)?)\s*-\s*(\d{2}):(\d{2}(?:\.\d+)?)\]\s+(.+?)\s*:\s+(.*)"
    )
    re_no_ts = re.compile(r"^(.+?):\s+(.+)$")
    segments: list[dict] = []

    with open(txt_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            m = re_with_ts_range.match(line)
            if m:
                mm1, ss1, mm2, ss2, speaker_raw, text = m.groups()
                start = int(mm1) * 60 + float(ss1)
                end = int(mm2) * 60 + float(ss2)
                segments.append({
                    "start": float(start),
                    "end": float(end),
                    "speaker": speaker_raw.strip(),
                    "text": text.strip(),
                })
                continue
            m = re_with_ts.match(line)
            if m:
                hh, mm, ss, speaker_raw, text = m.groups()
                start = int(hh) * 3600 + int(mm) * 60 + int(ss)
                end = start + max(len(text) * 0.05, 1.0)
                segments.append({
                    "start": float(start),
                    "end": float(end),
                    "speaker": speaker_raw.strip(),
                    "text": text.strip(),
                })
                continue
            m = re_with_ts_short.match(line)
            if m:
                mm, ss, speaker_raw, text = m.groups()
                start = int(mm) * 60 + int(ss)
                end = start + max(len(text) * 0.05, 1.0)
                segments.append({
                    "start": float(start),
                    "end": float(end),
                    "speaker": speaker_raw.strip(),
                    "text": text.strip(),
                })
                continue
            m = re_no_ts.match(line)
            if m:
                segments.append({
                    "start": float(i),
                    "end": float(i + 1),
                    "speaker": m.group(1).strip(),
                    "text": m.group(2).strip(),
                })
                continue

    segments.sort(key=lambda s: s["start"])
    log.info(f"{len(segments)} segments chargés.")
    return segments


# ---------------------------------------------------------------------------
# Étape 1 : Fenêtres glissantes
# ---------------------------------------------------------------------------
@dataclass
class TextWindow:
    index: int
    start_time: float
    end_time: float
    text: str
    segment_indices: list[int] = field(default_factory=list)


def build_windows(segments: list[dict], window_size: int) -> list[TextWindow]:
    """Fenêtres glissantes (slide=1) de window_size segments concaténés."""
    windows: list[TextWindow] = []
    n = len(segments)

    for i in range(n - window_size + 1):
        chunk = segments[i:i + window_size]
        lines = []
        for seg in chunk:
            speaker = seg.get("speaker", "?")
            text = seg.get("text", "").strip()
            if text:
                lines.append(f"[{speaker}]: {text}")

        text = "\n".join(lines)
        if not text.strip():
            continue

        windows.append(TextWindow(
            index=len(windows),
            start_time=chunk[0].get("start", 0.0),
            end_time=chunk[-1].get("end", 0.0),
            text=text,
            segment_indices=list(range(i, i + window_size)),
        ))

    log.info(f"{len(windows)} fenêtres créées (window_size={window_size}, slide=1).")
    return windows


# ---------------------------------------------------------------------------
# Étape 2 : Embeddings
# ---------------------------------------------------------------------------
_EMBED_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def _get_embed_model(model_name: str) -> SentenceTransformer:
    if model_name not in _EMBED_MODEL_CACHE:
        resolved = model_name
        minilm_dir = os.environ.get("MINILM_DIR")
        if minilm_dir and model_name == "all-MiniLM-L6-v2" and Path(minilm_dir).is_dir():
            resolved = minilm_dir
        log.info(f"Chargement modèle d'embedding : {resolved}")
        _EMBED_MODEL_CACHE[model_name] = SentenceTransformer(resolved, device="cpu")
    return _EMBED_MODEL_CACHE[model_name]


def embed_windows(windows: list[TextWindow], model_name: str, batch_size: int) -> np.ndarray:
    model = _get_embed_model(model_name)
    texts = [w.text for w in windows]
    log.info(f"Embedding de {len(texts)} fenêtres...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    log.info(f"Embeddings : {embeddings.shape}")
    return embeddings


# ---------------------------------------------------------------------------
# Étape 3 : Détection des frontières
# ---------------------------------------------------------------------------
def detect_topic_boundaries(
    embeddings: np.ndarray,
    sigma: float,
    percentile: float,
    min_distance: int,
) -> tuple[list[int], np.ndarray, np.ndarray]:
    """Détecte les frontières via les chutes de similarité cosine."""
    n = len(embeddings)
    if n < 2:
        return [], np.array([]), np.array([])

    raw_similarities = np.array([
        float(np.dot(embeddings[i], embeddings[i + 1]))
        for i in range(n - 1)
    ])
    log.info(f"Similarités : min={raw_similarities.min():.3f}, "
             f"max={raw_similarities.max():.3f}, "
             f"mean={raw_similarities.mean():.3f}")

    if sigma > 0 and len(raw_similarities) > 3:
        smoothed = gaussian_filter1d(raw_similarities, sigma=sigma)
    else:
        smoothed = raw_similarities.copy()

    threshold = np.percentile(smoothed, percentile)
    log.info(f"Seuil (percentile {percentile}%) = {threshold:.3f}")

    candidates = [i for i in range(len(smoothed)) if smoothed[i] < threshold]

    boundaries: list[int] = []
    last_boundary = -min_distance
    for idx in candidates:
        if idx - last_boundary >= min_distance:
            boundaries.append(idx)
            last_boundary = idx
        elif smoothed[idx] < smoothed[boundaries[-1]]:
            boundaries[-1] = idx
            last_boundary = idx

    log.info(f"Frontières détectées : {len(boundaries)} coupures")
    for b in boundaries:
        log.info(f"  → fenêtre {b}, similarité={smoothed[b]:.3f}")

    return boundaries, raw_similarities, smoothed


# ---------------------------------------------------------------------------
# Étape 4 : Chunks thématiques
# ---------------------------------------------------------------------------
@dataclass
class TopicChunk:
    chunk_id: int
    start_time: float
    end_time: float
    segments: list[dict]
    text: str


def _segments_to_text(chunk_segs: list[dict]) -> str:
    lines = []
    for seg in chunk_segs:
        spk = seg.get("speaker", "?")
        txt = seg.get("text", "").strip()
        if txt:
            lines.append(f"[{spk}]: {txt}")
    return "\n".join(lines)


def _chars(chunk_segs: list[dict]) -> int:
    return len(_segments_to_text(chunk_segs))


def _resplit_semantic(
    chunk_segs: list[dict],
    max_chunk_chars: int,
    model_name: str,
    batch_size: int,
    window_size: int,
    sigma: float,
) -> list[list[dict]]:
    """Re-coupe récursivement un chunk trop gros à sa vallée de similarité la plus profonde."""
    if len(chunk_segs) < max(4, window_size + 1):
        mid = len(chunk_segs) // 2
        return [chunk_segs[:mid], chunk_segs[mid:]] if mid > 0 else [chunk_segs]

    sub_windows = build_windows(chunk_segs, window_size)
    if len(sub_windows) < 2:
        mid = len(chunk_segs) // 2
        return [chunk_segs[:mid], chunk_segs[mid:]]

    model = _get_embed_model(model_name)
    embs = model.encode(
        [w.text for w in sub_windows],
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    sims = np.array([float(np.dot(embs[i], embs[i + 1])) for i in range(len(embs) - 1)])
    if len(sims) == 0:
        mid = len(chunk_segs) // 2
        return [chunk_segs[:mid], chunk_segs[mid:]]
    smoothed = gaussian_filter1d(sims, sigma=sigma) if len(sims) > 3 and sigma > 0 else sims

    best = int(np.argmin(smoothed))
    cut_seg = best + 1
    left = chunk_segs[:cut_seg]
    right = chunk_segs[cut_seg:]
    if not left or not right:
        mid = len(chunk_segs) // 2
        return [chunk_segs[:mid], chunk_segs[mid:]]

    log.info(f"  ↳ re-split sémantique : {len(chunk_segs)} segs → "
             f"{len(left)}+{len(right)} (vallée à fenêtre {best}, sim={smoothed[best]:.3f})")

    results: list[list[dict]] = []
    for part in (left, right):
        if _chars(part) > max_chunk_chars and len(part) >= max(4, window_size + 1):
            results.extend(_resplit_semantic(
                part, max_chunk_chars, model_name, batch_size, window_size, sigma
            ))
        else:
            results.append(part)
    return results


def build_topic_chunks(
    segments: list[dict],
    windows: list[TextWindow],
    boundaries: list[int],
    max_chunk_chars: int,
    cfg: "Config | None" = None,
) -> list[TopicChunk]:
    """Découpe aux frontières + re-split sémantique si trop gros."""
    seg_boundaries = sorted(set(b + 1 for b in boundaries))
    cut_points = sorted(set([0] + seg_boundaries + [len(segments)]))

    chunks: list[TopicChunk] = []
    chunk_id = 0

    for i in range(len(cut_points) - 1):
        start_idx = cut_points[i]
        end_idx = cut_points[i + 1]
        chunk_segs = segments[start_idx:end_idx]

        if not chunk_segs:
            continue

        chunk_text = _segments_to_text(chunk_segs)
        if not chunk_text.strip():
            continue

        if len(chunk_text) > max_chunk_chars and len(chunk_segs) >= 4 and cfg is not None:
            sub_parts = _resplit_semantic(
                chunk_segs,
                max_chunk_chars=max_chunk_chars,
                model_name=cfg.embedding_model,
                batch_size=cfg.embedding_batch_size,
                window_size=cfg.boundary_window_size,
                sigma=cfg.boundary_smoothing_sigma,
            )
            for sub_segs in sub_parts:
                sub_text = _segments_to_text(sub_segs)
                if sub_text.strip():
                    chunks.append(TopicChunk(
                        chunk_id=chunk_id,
                        start_time=sub_segs[0].get("start", 0.0),
                        end_time=sub_segs[-1].get("end", 0.0),
                        segments=sub_segs,
                        text=sub_text,
                    ))
                    chunk_id += 1
        else:
            chunks.append(TopicChunk(
                chunk_id=chunk_id,
                start_time=chunk_segs[0].get("start", 0.0),
                end_time=chunk_segs[-1].get("end", 0.0),
                segments=chunk_segs,
                text=chunk_text,
            ))
            chunk_id += 1

    log.info(f"{len(chunks)} chunks thématiques créés")
    for c in chunks:
        dur = c.end_time - c.start_time
        log.info(f"  Chunk {c.chunk_id} : {len(c.segments)} segs, "
                 f"{len(c.text)} chars, {c.start_time:.0f}s → {c.end_time:.0f}s "
                 f"({dur:.0f}s)")

    return chunks


# ---------------------------------------------------------------------------
# LLM — llama-server.exe
# ---------------------------------------------------------------------------
_server_process: subprocess.Popen | None = None


def _server_ram_mb() -> float:
    """RAM du process llama-server (+ enfants) en Mo."""
    if not _server_process or _server_process.poll() is not None:
        return 0.0
    try:
        proc = psutil.Process(_server_process.pid)
        mem = proc.memory_info().rss
        for child in proc.children(recursive=True):
            mem += child.memory_info().rss
        return mem / 1024 / 1024
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


def _kill_server() -> None:
    global _server_process
    if _server_process and _server_process.poll() is None:
        log.info("Arrêt llama-server...")
        _server_process.terminate()
        try:
            _server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        _server_process = None


def _kill_port(port: int) -> None:
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True)
        port_bytes = f":{port}".encode()
        for line in result.stdout.splitlines():
            if port_bytes in line and b"LISTENING" in line:
                pid = line.strip().split()[-1].decode()
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                log.info(f"Port {port} libéré (PID {pid}).")
                time.sleep(2)
    except Exception:
        pass


def start_llm_server_slots(cfg: Config, parallel_slots: int) -> None:
    """Démarre llama-server avec --parallel N. ctx-size CONSTANT — llama.cpp
    le split en N slots de (total_ctx / N) tokens chacun. Le KV cache RAM
    est dimensionné par total_ctx, pas par parallel_slots, donc bumper N
    ne coûte pas de RAM tant que chaque chunk tient dans (total_ctx / N).
    Ordre de grandeur FR : 1 token ≈ 3-4 chars. À 32k ctx total et N=2,
    chaque slot a 16k tokens → digère sans souci des chunks ≤ 30k chars."""
    global _server_process
    _kill_port(cfg.llm_server_port)

    if not Path(cfg.llama_server_exe).exists():
        raise FileNotFoundError(f"llama-server introuvable : {cfg.llama_server_exe}")
    if not Path(cfg.llm_model_path).exists():
        raise FileNotFoundError(f"Modèle introuvable : {cfg.llm_model_path}")

    # ctx-size 16384 (vs 32768 avant) : avec max_chunk_chars=15000
    # (~3750 tokens) + system + instructions + output (~400), un ctx de 16k
    # est largement suffisant. Moitie de KV-cache RAM, prefill plus rapide,
    # et evite les ralentissements observes sur ik_llama avec gros ctx.
    total_ctx = cfg.llm_n_ctx if cfg.llm_n_ctx > 0 else 16384
    cmd = [
        cfg.llama_server_exe,
        "-m", cfg.llm_model_path,
        "--port", str(cfg.llm_server_port),
        "--ctx-size", str(total_ctx),
        "--parallel", str(parallel_slots),
        # Flash Attention : prerequis pour KV-quant safe sur la plupart des
        # archis (sinon ik_llama boucle sans EOS, mainline tombe en fallback
        # non-optimise). Aussi : +10-25% TG via online softmax block-by-block.
        "--flash-attn", "on",
        # Cache RAM (host-memory prompt cache, -cram) desactive.
        # ik_llama default = 8192 MiB qui sature la RAM apres ~10 chunks et cause
        # OOM kill silencieux par Windows. Le prefix-cache par slot (toujours
        # actif, non concerne par ce flag) suffit pour cache hit cross-prompt
        # sur le meme chunk (RESUME -> EXTRACTION -> PLAN).
        # Mainline supporte aussi --cache-ram, valeur 0 = disable identique.
        "--cache-ram", "0",
        # KV cache quantization — decode is bandwidth-bound on CPU
        "--cache-type-k", cfg.llm_kv_cache_type,
        "--cache-type-v", cfg.llm_kv_cache_type,
        # Flags retires :
        # - --cache-reuse 256 : aucun gain mesurable (prefix-cache natif suffit),
        #   et pas supporte par ik_llama.cpp.
        # - --fit off : controle GPU offload auto-fit, sans effet sur CPU-only
        #   (llm_n_gpu_layers=0 chez nous), incompatible avec la syntaxe ik_llama.
    ]
    # Logs llama-server : silencieux par defaut (--log-disable), verbeux si
    # LLAMA_VERBOSE=1 (utile pour diagnostiquer le cache, n_past, batch.n_tokens
    # dans _llama_server_stderr.log).
    if os.environ.get("LLAMA_VERBOSE") != "1":
        cmd.append("--log-disable")
    # Larger prefill batches. Toggleable via env var LLM_FAST_FLAGS
    # (default "1" = on). Set "0" to disable for A/B.
    #
    # PLD retiré : bench A/B 2026-05 a montré une régression -5 % sur RESUME
    # (output abstractif court → acceptance rate trop bas, verify pass coûte
    # plus qu'il rapporte) et neutre sur EXTRACTION / PLAN (output JSON court).
    if os.environ.get("LLM_FAST_FLAGS", "1") != "0":
        cmd += [
            "--batch-size", "4096",
            "--ubatch-size", "1024",
        ]
    if cfg.llm_n_threads:
        cmd += ["--threads", str(cfg.llm_n_threads)]
    if cfg.llm_n_gpu_layers:
        cmd += ["-ngl", str(cfg.llm_n_gpu_layers)]

    log.info(f"Démarrage llama-server (parallel={parallel_slots}, ctx_total={total_ctx})...")
    log.info(f"  cmd: {' '.join(cmd)}")
    stderr_log = Path("_llama_server_stderr.log")
    t0 = time.time()
    verbose_console = os.environ.get("LLAMA_VERBOSE") == "1"
    if verbose_console:
        # Logs llama-server affiches DIRECTEMENT en console (stderr du process)
        # au lieu d'etre rediriges dans le fichier. Pratique pour diagnostiquer
        # en live (cache hit, n_past, etc.).
        _stderr_fh = None
        stderr_target = None
    else:
        _stderr_fh = open(stderr_log, "w", encoding="utf-8", errors="replace")
        stderr_target = _stderr_fh
    _server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=stderr_target,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    atexit.register(_kill_server)

    health_url = f"http://{cfg.llm_server_host}:{cfg.llm_server_port}/health"
    deadline = time.time() + cfg.llm_server_startup_timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as r:
                if r.status == 200:
                    log_perf(f"llama-server démarré (slots={parallel_slots})", t0)
                    return
        except Exception:
            pass
        if _server_process.poll() is not None:
            if _stderr_fh is not None:
                _stderr_fh.flush(); _stderr_fh.close()
                tail = stderr_log.read_text(encoding="utf-8", errors="replace")[-2000:]
            else:
                tail = "(logs llama-server en mode --verbose, voir console)"
            raise RuntimeError(
                f"llama-server s'est arrêté prématurément. Stderr (dernières 2000 chars) :\n{tail}"
            )
        time.sleep(1)
    raise TimeoutError(f"llama-server timeout ({cfg.llm_server_startup_timeout}s)")


# ---------------------------------------------------------------------------
# Entités figées — rappel inline en fin de prompt utilisateur
# ---------------------------------------------------------------------------
def _entity_reminder() -> str:
    """Rappel court injecté en fin de prompt utilisateur quand des entités sont fournies."""
    import os as _os
    participants = (_os.environ.get("MEETING_PARTICIPANTS") or "").strip()
    entreprises = (_os.environ.get("MEETING_ENTREPRISES") or "").strip()
    if not participants and not entreprises:
        return ""
    block = [
        "\n\n--- RAPPEL ENTITÉS (VÉRITÉ ABSOLUE) ---",
        "Reproduis chaque nom EXACTEMENT comme dans les listes ci-dessous "
        "(casse, accents, espaces). Corrige silencieusement toute variante ASR. "
        "Ne cite AUCUNE personne ou entreprise absente de ces listes.",
    ]
    if participants:
        block.append(f"PARTICIPANTS : {participants}")
    if entreprises:
        block.append(f"ENTREPRISES : {entreprises}")
    return "\n".join(block)


def _build_system_prompt() -> str:
    """System prompt de base + contexte + entités figées (env MEETING_*)."""
    import os as _os
    base = (
        "Tu es un assistant expert en rédaction de comptes rendus professionnels. "
        "Réponds uniquement en français.\n"
        "- Ne mentionne QUE ce qui est EXPLICITEMENT dit dans le texte fourni.\n"
        "- N'invente JAMAIS d'informations, décisions, actions, chiffres, dates, échéances.\n"
        "- Ne développe JAMAIS un sigle ou acronyme.\n"
        "- Si aucune décision : 'Aucune décision prise'. Si aucune action : 'Aucune action définie'.\n"
    )

    participants = (_os.environ.get("MEETING_PARTICIPANTS") or "").strip()
    entreprises  = (_os.environ.get("MEETING_ENTREPRISES")  or "").strip()

    if participants or entreprises:
        base += (
            "\n=== ENTITÉS FIGÉES — PRIORITÉ ABSOLUE sur le transcript ASR ===\n"
            "Les listes ci-dessous sont la vérité. Le transcript contient des erreurs phonétiques "
            "sur les noms propres : corrige-les silencieusement vers la forme EXACTE de la liste "
            "(casse, accents, espaces, caractère pour caractère).\n"
            "Toute forme proche (phonétique, partielle) d'un nom de la liste DOIT être remplacée "
            "par la forme exacte. Si un nom du transcript ne matche AUCUN élément de la liste, "
            "ne le cite pas (probable erreur ASR). Ne déduis jamais qu'une personne appartient "
            "à une entreprise sans mention explicite.\n"
        )
        if participants:
            base += f"PARTICIPANTS (forme EXACTE) : {participants}\n"
        if entreprises:
            base += f"ENTREPRISES (forme EXACTE) : {entreprises}\n"

    ctx = (_os.environ.get("MEETING_CONTEXT") or "").strip()
    if ctx:
        base += (
            "\n=== CONTEXTE RÉUNION ===\n"
            "À utiliser pour lever les ambiguïtés sur les sigles. N'invente rien d'absent du transcript.\n"
            + ctx
        )
    return base


def llm_complete(prompt: str, cfg: Config, timeout: int = 300,
                 json_schema: dict | None = None) -> str:
    """Appelle llama-server. Si json_schema fourni, contraint la sortie."""
    url = f"http://{cfg.llm_server_host}:{cfg.llm_server_port}/v1/chat/completions"
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        "temperature": cfg.llm_temperature,
        "top_k": 50,
        "repeat_penalty": cfg.llm_repeat_penalty,
        "stop": ["<|end|>", "<|endoftext|>", "<|im_end|>", "</s>"],
    }
    if json_schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "section", "strict": True, "schema": json_schema},
        }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
# Structure document-first / instruction-last : le chunk est en tete pour
# maximiser la reutilisation du KV cache entre RESUME et EXTRACTION via
# llama-server --cache-reuse. Voir LLAMA_CACHE_REUSE_DEEP_DIVE.md pour le
# detail technique et la litterature academique (Liu et al. TACL 2024,
# Anthropic +30%, vLLM/SGLang prefix caching).
PROMPT_RESUME = """\
Extrait :
{texte}

---

Résume cet extrait de réunion en UN objet JSON.

RÈGLES :
- titre : court et précis, sujet principal de l'extrait
- contexte : UNE phrase qui résume le sujet
- points : 3 à 5 bullets factuels, chacun UNE phrase courte autonome (qui, quoi, pourquoi). Pas de transition ("ensuite", "puis"), pas de redite du contexte.
- Style sobre, pas d'opinion.
- N'INVENTE RIEN. Ne développe pas les sigles.

FORMAT JSON STRICT, rien d'autre :
{{"titre": "string", "contexte": "string", "points": ["string", "string", "string"]}}"""

PROMPT_EXTRACTION = """\
Extrait :
{texte}

---

Extrais les décisions de cet extrait de réunion. Produis UN objet JSON.

RÈGLE ABSOLUE : EXTRACTION PURE. Ne liste QUE ce qui est EXPLICITEMENT dit.

DÉCISION = choix ACTÉ par le groupe ("on décide de", "on valide", "c'est acté").
- Une discussion ou exploration d'options N'EST PAS une décision.
- Un engagement à faire une action future N'EST PAS une décision (plan d'attaque, traité ailleurs).
- Si rien n'est acté, tableau vide.

EXEMPLES DE FORMAT — fictifs et illustratifs. N'EXTRAIS JAMAIS leur contenu :
ne te sers QUE de l'extrait ci-dessus.
« J'ai développé un outil N8N avec plusieurs agents. » → {{"decisions": []}}
« On pourrait faire un atelier UX un jour. » → {{"decisions": []}}
« [EXEMPLE FICTIF] On valide un passage en production. » → {{"decisions": ["<décision actée telle que dite dans l'extrait>"]}}

FORMAT JSON STRICT, rien d'autre :
{{"decisions": ["string", ...]}}"""

PROMPT_PLAN_ATTACK = """\
Tu es un consultant senior. Voici le compte rendu (sujets + décisions). Construis un Plan d'attaque : liste priorisée d'actions concrètes post-réunion.

DEUX TYPES d'items mélangés :
1. ENGAGEMENTS EXPLICITES (priorité haute) : actions promises dans le transcript ("je vais X", "on organise Y", "d'ici fin de semaine"). Reprends responsable et échéance EXACTEMENT tels que mentionnés, sans invention.
2. RECOMMANDATIONS CONSULTANT (2 à 4 items) : actions de bon sens à suggérer. Pour ces items, "—" en responsable et "—" en échéance.

RÈGLES :
- 4 à 10 items total.
- Chaque item rattaché à un sujet (champ `sujet`).
- Ne reformule pas une décision déjà listée ailleurs.
- N'invente JAMAIS un responsable ni une échéance absents du transcript.
- "—" partout où l'info n'est pas explicite.
- Ne développe pas les sigles.

FORMAT JSON STRICT, rien d'autre :
{{"plan": [{{"action": "string", "sujet": "string", "responsable": "string ou —", "echeance": "string ou —"}}]}}

Matière :
{contenu}"""

PROMPT_SPEAKER_MAPPING = """\
Voici les noms des participants à cette réunion (LISTE FERMÉE — vérité absolue) :
{participants}

Entreprises impliquées (LISTE FERMÉE — vérité absolue) :
{entreprises}

Voici le début du transcript. Les locuteurs sont identifiés par des IDs anonymes (SPEAKER_00, SPEAKER_01, etc.).
En lisant les présentations, associe chaque SPEAKER_XX au nom réel ET à son entreprise.

RÈGLES IMPÉRATIVES :
- Le champ "nom" DOIT être un élément EXACT de la liste des participants ci-dessus, ou null. Jamais une variante, jamais un nom extrait directement du transcript sans correspondance dans la liste.
- Le champ "entreprise" DOIT être un élément EXACT de la liste des entreprises ci-dessus, ou null. JAMAIS une variante orthographique entendue dans le transcript.
- Le transcript peut contenir des erreurs de transcription : "Élé Consulting" pour "Yele Consulting", "Sureau" pour "RTE", etc. Ignore ces variantes et utilise UNIQUEMENT les formes exactes des listes fermées.
- Base-toi sur ce que les personnes disent d'elles-mêmes ("moi c'est X", "je suis chez Y") pour faire le rapprochement phonétique avec les listes.
- Si aucun élément de la liste des participants ne correspond phonétiquement à ce que dit un SPEAKER, mets null pour le nom.
- Si aucune entreprise de la liste ne correspond phonétiquement, mets null.
- Chaque nom de la liste ne peut être assigné qu'à UN SEUL speaker.

FORMAT DE SORTIE — JSON STRICT, rien d'autre :
{{
  "mapping": {{
    "SPEAKER_00": {{"nom": "Prénom NOM ou null", "entreprise": "nom entreprise ou null"}},
    "SPEAKER_01": {{"nom": "Prénom NOM ou null", "entreprise": "nom entreprise ou null"}},
    "SPEAKER_02": {{"nom": "Prénom NOM ou null", "entreprise": "nom entreprise ou null"}}
  }}
}}

Transcript (début) :
{intro}"""

PROMPT_EXEC_SUMMARY = """\
Voici le début du transcript d'une réunion + les titres/résumés de chaque section. Rédige un Executive Summary de 5 phrases.

OBJECTIF : but global, grands thèmes, conclusion. PAS de résumé section par section, vision de haut niveau.

RÈGLES :
- N'invente aucune information.
- Ne développe pas les sigles.
- Pas de listes, pas de titres : un paragraphe.

--- DÉBUT TRANSCRIPT ---
{intro}

--- SECTIONS ---
{contenu}"""

# Per-chunk : extrait les items du plan d'attaque (engagements + suggestions)
# en UN SEUL appel LLM. Document-first → HIT cache reuse sur [system][chunk]
# entre résumé/extraction/plan du MÊME chunk. Voir LLAMA_CACHE_REUSE_DEEP_DIVE.md.
#
# Cap matériel via SCHEMA_PLAN_PERCHUNK.maxItems (grammar GBNF côté llama-server)
# + pression "rien si rien" en prompt (cf. PROMPT_EXTRACTION pour les décisions).
PROMPT_PLAN_PERCHUNK = """\
Extrait :
{texte}

---

Extrais les ACTIONS POST-RÉUNION concrètes de cet extrait. Produis UN objet JSON.

DEUX TYPES D'ITEMS :
1. ENGAGEMENT : action promise EXPLICITEMENT ("je vais X", "on organise Y", "d'ici vendredi").
   → Responsable et échéance EXACTEMENT tels que mentionnés.
2. SUGGESTION : action de bon sens qui découle du sujet, sans avoir été promise.
   → Responsable et échéance toujours "—".

RÈGLE ABSOLUE — RIEN SI RIEN :
- Mieux vaut un tableau vide qu'une action forcée.
- Recap, smalltalk, tour de table, présentation pendant la réunion → [].
- Action faite PENDANT la réunion ("je vais vous présenter…") N'EST PAS post-réunion.
- Mention d'un outil/modèle DÉJÀ existant N'EST PAS une action future.
- Décision actée sans suite N'EST PAS un item de plan.

INTERDICTIONS :
- Pas de méta-commentaire ("à vérifier", "supposons que…", "non explicitement nommé").
- Jamais "SPEAKER_XX" en responsable → "—".
- N'invente JAMAIS un responsable ni une échéance.

LIMITE STRICTE : 0 à 2 items max.

EXEMPLES DE FORMAT — fictifs et illustratifs. N'EXTRAIS JAMAIS leur contenu :
ne te sers QUE de l'extrait ci-dessus. Si une phrase d'exemple n'apparaît pas
dans l'extrait, elle ne doit PAS figurer dans ta sortie.
« Je vais vous présenter le projet RTE. » → {{"plan": []}}
« On a un modèle pour la congestion développé chez RTE. » → {{"plan": []}}
« [EXEMPLE FICTIF] Quelqu'un s'occupe d'un livrable pour une échéance donnée. » → {{"plan": [{{"action": "<action telle que dite>", "responsable": "<nom tel que dit>", "echeance": "<échéance telle que dite>", "type": "engagement"}}]}}
« [EXEMPLE FICTIF] On évoque une piste sans l'avoir promise. » → {{"plan": [{{"action": "<piste reformulée>", "responsable": "—", "echeance": "—", "type": "suggestion"}}]}}

FORMAT JSON STRICT, rien d'autre :
{{"plan": [{{"action": "string", "responsable": "string ou —", "echeance": "string ou —", "type": "engagement | suggestion"}}, ...]}}"""


# ---------------------------------------------------------------------------
# Schémas JSON forcés côté llama-server
# ---------------------------------------------------------------------------
SCHEMA_RESUME = {
    "type": "object",
    "properties": {
        "titre": {"type": "string"},
        "contexte": {"type": "string"},
        "points": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 6,
        },
    },
    "required": ["titre", "contexte", "points"],
    "additionalProperties": False,
}

SCHEMA_EXTRACTION = {
    "type": "object",
    "properties": {
        "decisions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["decisions"],
    "additionalProperties": False,
}

SCHEMA_PLAN_ATTACK = {
    "type": "object",
    "properties": {
        "plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "sujet": {"type": "string"},
                    "responsable": {"type": "string"},
                    "echeance": {"type": "string"},
                },
                "required": ["action", "sujet", "responsable", "echeance"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["plan"],
    "additionalProperties": False,
}

SCHEMA_PLAN_PERCHUNK = {
    "type": "object",
    "properties": {
        "plan": {
            "type": "array",
            "maxItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "responsable": {"type": "string"},
                    "echeance": {"type": "string"},
                    "type": {"type": "string", "enum": ["engagement", "suggestion"]},
                },
                "required": ["action", "responsable", "echeance", "type"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["plan"],
    "additionalProperties": False,
}

SCHEMA_SPEAKER_MAPPING = {
    "type": "object",
    "properties": {
        "mapping": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "nom": {"type": "string"},
                    "entreprise": {"type": "string"},
                },
                "required": ["nom", "entreprise"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["mapping"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Parsing robuste JSON
# ---------------------------------------------------------------------------
def _parse_json_safe(raw: str, chunk_id: int) -> dict:
    """Extraction JSON robuste depuis une réponse LLM."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as e:
            log.warning(f"Chunk {chunk_id}: JSON invalide ({e}).")
    return {}


# ---------------------------------------------------------------------------
# Échantillonneur RAM
# ---------------------------------------------------------------------------
class RamSampler:
    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.samples_server: list[float] = []
        self.samples_system: list[float] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample(self) -> None:
        while not self._stop.is_set():
            self.samples_server.append(_server_ram_mb())
            self.samples_system.append(ram_total_mb())
            self._stop.wait(self.interval)

    def start(self) -> None:
        self._stop.clear()
        self.samples_server.clear()
        self.samples_system.clear()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def peak_server(self) -> float:
        return max(self.samples_server) if self.samples_server else 0.0

    def peak_system(self) -> float:
        return max(self.samples_system) if self.samples_system else 0.0

    def avg_server(self) -> float:
        return sum(self.samples_server) / len(self.samples_server) if self.samples_server else 0.0


# ---------------------------------------------------------------------------
# Génération par chunk (2 ou 3 appels LLM selon cfg.plan_attack_mode)
# ---------------------------------------------------------------------------
def generate_section_json(chunk: TopicChunk, cfg: Config) -> dict:
    """Appels LLM par chunk : résumé + extraction (toujours), et en mode
    "perchunk", un appel supplémentaire (plan d'attaque unifié engagement +
    suggestion) qui bénéficie du HIT cache sur [system][chunk] (document-first).
    """
    log.info(f"  → LLM chunk {chunk.chunk_id} ({len(chunk.segments)} segs, ~{len(chunk.text)} chars)")

    reminder = _entity_reminder()

    t0 = time.time()
    raw_resume = llm_complete(
        PROMPT_RESUME.format(texte=chunk.text) + reminder, cfg,
        timeout=cfg.llm_section_timeout,
        json_schema=SCHEMA_RESUME,
    )
    log_perf(f"Chunk {chunk.chunk_id} résumé", t0)

    t1 = time.time()
    raw_extract = llm_complete(
        PROMPT_EXTRACTION.format(texte=chunk.text) + reminder, cfg,
        timeout=cfg.llm_section_timeout,
        json_schema=SCHEMA_EXTRACTION,
    )
    log_perf(f"Chunk {chunk.chunk_id} extraction", t1)

    raw_plan: str = ""
    plan_data: dict = {}
    if cfg.plan_attack_mode == "perchunk":
        t2 = time.time()
        raw_plan = llm_complete(
            PROMPT_PLAN_PERCHUNK.format(texte=chunk.text) + reminder, cfg,
            timeout=cfg.llm_section_timeout,
            json_schema=SCHEMA_PLAN_PERCHUNK,
        )
        log_perf(f"Chunk {chunk.chunk_id} plan", t2)
        plan_data = _parse_json_safe(raw_plan, chunk.chunk_id)

    resume_data = _parse_json_safe(raw_resume, chunk.chunk_id)
    extract_data = _parse_json_safe(raw_extract, chunk.chunk_id)

    contexte = str(resume_data.get("contexte") or "").strip()
    points = [
        str(p).strip()
        for p in (resume_data.get("points") or [])
        if str(p).strip()
    ]
    # `resume` (texte combiné) reste utilisé par build_exec_summary /
    # build_plan_attack, et sert de fallback d'affichage si points/contexte
    # sont vides.
    if contexte or points:
        resume = contexte
        if points:
            if resume:
                resume += "\n"
            resume += "\n".join(f"- {p}" for p in points)
    else:
        resume = str(resume_data.get("resume") or raw_resume.strip()).strip()

    # Plan d'attaque per-chunk : engagement (responsable/échéance tels quels,
    # filet anti-SPEAKER_XX) + suggestion (responsable/échéance forcés "—").
    plan_items: list[dict] = []
    for item in (plan_data.get("plan") or []):
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "").strip()
        if not action:
            continue
        item_type = str(item.get("type") or "suggestion").strip().lower()
        if item_type not in ("engagement", "suggestion"):
            item_type = "suggestion"
        if item_type == "engagement":
            resp = str(item.get("responsable") or "—").strip() or "—"
            if re.match(r"^SPEAKER_\d+$", resp):
                resp = "—"
            ech = str(item.get("echeance") or "—").strip() or "—"
        else:
            resp = "—"
            ech = "—"
        plan_items.append({
            "action": action,
            "responsable": resp,
            "echeance": ech,
            "type": item_type,
        })

    return {
        "titre": str(resume_data.get("titre") or f"Sujet {chunk.chunk_id + 1}").strip(),
        "contexte": contexte,
        "points": points,
        "resume": resume,
        "decisions": [str(d).strip() for d in (extract_data.get("decisions") or []) if str(d).strip()],
        "plan": plan_items,
        "_raw_resume": raw_resume,
        "_raw_extract": raw_extract,
        "_raw_plan": raw_plan,
        "_chunk_id": chunk.chunk_id,
        "_start_time": chunk.start_time,
        "_end_time": chunk.end_time,
        # Texte brut transcrit du chunk — source de verite pour les workers
        # agentiques (Ou & Lapata ACL Findings 2025 : context-aware merging
        # reduit l'amplification d'hallucinations vs merge sur resumes seuls).
        "_chunk_text": chunk.text,
    }


# ---------------------------------------------------------------------------
# Speaker mapping
# ---------------------------------------------------------------------------
def resolve_speaker_mapping(transcript_path: str, participants: str,
                            entreprises: str, cfg: Config) -> dict[str, dict]:
    """Appel LLM pour mapper SPEAKER_XX → {nom, entreprise} via le tour de table."""
    with open(transcript_path, "r", encoding="utf-8") as f:
        intro = "".join(line for _, line in zip(range(80), f))

    prompt = PROMPT_SPEAKER_MAPPING.format(
        participants=participants,
        entreprises=entreprises,
        intro=intro,
    )
    log.info("Résolution speaker mapping via LLM...")
    t0 = time.time()
    raw = llm_complete(prompt, cfg, timeout=cfg.llm_section_timeout,
                       json_schema=SCHEMA_SPEAKER_MAPPING)
    log_perf("Speaker mapping", t0)
    data = _parse_json_safe(raw, -1)
    raw_mapping = data.get("mapping", {})
    mapping = {}
    for k, v in raw_mapping.items():
        if isinstance(v, dict):
            nom = v.get("nom") or None
            if nom and nom.lower() != "null":
                mapping[k] = {
                    "nom": nom,
                    "entreprise": v.get("entreprise") if v.get("entreprise", "").lower() != "null" else None,
                }
    log.info(f"Speaker mapping résolu : {mapping}")
    return mapping


def apply_speaker_mapping(segments: list, mapping: dict[str, dict]) -> list:
    """Remplace les SPEAKER_XX par les vrais noms dans le champ speaker."""
    if not mapping:
        return segments
    for seg in segments:
        speaker = seg.get("speaker", "")
        if speaker in mapping:
            seg["speaker"] = mapping[speaker]["nom"]
    return segments


# ---------------------------------------------------------------------------
# Plan d'attaque — deux modes :
#   "legacy"   : 1 appel LLM final sur les résumés agrégés (pas de hit cache).
#   "perchunk" : assemblage déterministe du plan unifié extrait par chunk
#                pendant la réunion (1 appel LLM par chunk, hit cache sur
#                [system][chunk]). Pas d'appel LLM ici.
# Dispatch via cfg.plan_attack_mode.
# ---------------------------------------------------------------------------
def build_plan_attack_legacy(sections: list[dict], cfg: Config) -> list[dict]:
    """Appel LLM final : plan d'attaque unifié basé sur les sujets/décisions."""
    contenu_parts = []
    for i, s in enumerate(sections, 1):
        part = f"## {i}. {s['titre']}\n{s['resume']}"
        if s["decisions"]:
            part += "\nDécisions : " + "; ".join(s["decisions"])
        contenu_parts.append(part)
    contenu = "\n\n".join(contenu_parts)

    prompt = PROMPT_PLAN_ATTACK.format(contenu=contenu) + _entity_reminder()
    tokens_est = len(prompt) // 4
    log.info(f"Plan d'attaque (legacy, ~{tokens_est} tokens estimés)...")
    t0 = time.time()
    raw = llm_complete(prompt, cfg, timeout=cfg.llm_section_timeout,
                       json_schema=SCHEMA_PLAN_ATTACK)
    log_perf("Plan d'attaque (legacy)", t0)
    data = _parse_json_safe(raw, -1)
    return data.get("plan", [])


def build_plan_attack_perchunk(sections: list[dict], cfg: Config) -> list[dict]:
    """Assemblage déterministe (sans appel LLM) : agrège les items du plan
    extraits par chunk via generate_section_json. Sujet = titre de la
    section d'origine.

    Tri : engagements (priorité haute) avant suggestions, puis ordre des
    chunks. Cap matériel à 2 items/chunk garanti par SCHEMA_PLAN_PERCHUNK."""
    engagements: list[dict] = []
    suggestions: list[dict] = []
    for s in sections:
        sujet = (s.get("titre") or "—").strip() or "—"
        for item in (s.get("plan") or []):
            action = (item.get("action") or "").strip()
            if not action:
                continue
            row = {
                "action": action,
                "sujet": sujet,
                "responsable": item.get("responsable") or "—",
                "echeance": item.get("echeance") or "—",
            }
            if item.get("type") == "engagement":
                engagements.append(row)
            else:
                suggestions.append(row)

    plan = engagements + suggestions
    log.info(f"Plan d'attaque (perchunk) : {len(plan)} items assemblés "
             f"({len(engagements)} engagements + {len(suggestions)} suggestions, "
             f"sans appel LLM final)")
    return plan


def build_plan_attack(sections: list[dict], cfg: Config) -> list[dict]:
    """Dispatcher : choisit l'implémentation selon cfg.plan_attack_mode."""
    mode = (cfg.plan_attack_mode or "perchunk").lower()
    if mode == "legacy":
        return build_plan_attack_legacy(sections, cfg)
    if mode == "perchunk":
        return build_plan_attack_perchunk(sections, cfg)
    log.warning(f"plan_attack_mode inconnu '{mode}' — fallback perchunk")
    return build_plan_attack_perchunk(sections, cfg)


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------
def build_exec_summary(sections: list[dict], cfg: Config,
                       transcript_path: str | None = None) -> str:
    """Appel LLM sur intro transcript (50 premières lignes) + titres/résumés."""
    intro = ""
    if transcript_path:
        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                intro = "".join(line for _, line in zip(range(50), f))
        except Exception:
            pass
    contenu = "\n\n".join(
        f"- {s['titre']} : {s['resume']}" for s in sections
    )
    prompt = PROMPT_EXEC_SUMMARY.format(intro=intro, contenu=contenu) + _entity_reminder()
    tokens_est = len(prompt) // 4
    log.info(f"Executive Summary (~{tokens_est} tokens estimés)...")
    t0 = time.time()
    result = llm_complete(prompt, cfg, timeout=cfg.llm_section_timeout)
    log_perf("Executive Summary", t0)
    return result


# ---------------------------------------------------------------------------
# Assemblage Markdown déterministe
# ---------------------------------------------------------------------------
def assemble_report(sections: list[dict], exec_summary: str, source: str,
                    plan: list[dict] | None = None,
                    speaker_mapping: dict[str, dict] | None = None) -> str:
    lines: list[str] = []

    # Numérotation séquentielle : Participants peut être absent (enregistrement
    # sans speaker_mapping) → la section suivante doit alors devenir « 1. »,
    # pas « 2. ». Le compteur n'avance que pour les sections réellement émises.
    n = 0

    def _h(titre: str) -> str:
        nonlocal n
        n += 1
        return f"## {n}. {titre}\n"

    lines.append("# Compte rendu de réunion\n")

    # Participants
    if speaker_mapping:
        lines.append(_h("Participants"))
        by_company: dict[str, list[str]] = {}
        for info in speaker_mapping.values():
            company = info.get("entreprise") or "Non précisé"
            by_company.setdefault(company, []).append(info["nom"])
        for company, names in sorted(by_company.items()):
            lines.append(f"**{company}** : {', '.join(sorted(names))}\n")
        lines.append("")

    # Résumé (anciennement « Executive Summary » — libellé FR)
    lines.append(_h("Résumé"))
    lines.append(exec_summary.strip() + "\n")

    # Sujets abordés
    lines.append(_h("Sujets abordés"))
    for i, s in enumerate(sections, 1):
        lines.append(f"### {i}. {s['titre']}\n")
        contexte = (s.get("contexte") or "").strip()
        points = [p.strip() for p in (s.get("points") or []) if p.strip()]
        if contexte or points:
            if contexte:
                lines.append(contexte + "\n")
            for p in points:
                lines.append(f"- {p}")
            if points:
                lines.append("")
        else:
            lines.append(s["resume"].strip() + "\n")

        if s["decisions"]:
            lines.append("**Décisions :**\n")
            for d in s["decisions"]:
                lines.append(f"- {d}")
            lines.append("")

    # Décisions
    lines.append(_h("Décisions"))
    all_decisions = [(s["titre"], d) for s in sections for d in s["decisions"]]
    if all_decisions:
        lines.append("| # | Sujet | Décision |")
        lines.append("|---|-------|----------|")
        for i, (titre, d) in enumerate(all_decisions, 1):
            d_safe = d.replace("|", "\\|")
            lines.append(f"| {i} | {titre} | {d_safe} |")
        lines.append("")
    else:
        lines.append("_Aucune décision formellement prise._\n")

    # Plan d'attaque (engagements explicites + recommandations consultant)
    lines.append(_h("Plan d'attaque"))
    if plan:
        lines.append("| # | Sujet | Action | Responsable | Échéance |")
        lines.append("|---|-------|--------|-------------|----------|")
        for i, p in enumerate(plan, 1):
            sujet = (p.get("sujet") or "—").replace("|", "\\|")
            action = (p.get("action") or "").replace("|", "\\|")
            resp = p.get("responsable") or "—"
            ech = p.get("echeance") or "—"
            lines.append(f"| {i} | {sujet} | {action} | {resp} | {ech} |")
        lines.append("")
    else:
        lines.append("_Aucune action à planifier._\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sauvegarde courbe de similarité (debug / visu)
# ---------------------------------------------------------------------------
def save_similarity_debug(
    raw_sims: np.ndarray,
    smoothed: np.ndarray,
    boundaries: list[int],
    windows: list[TextWindow],
    output_path: str,
) -> None:
    debug_path = Path(output_path).with_suffix(".similarity.json")
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "raw_similarities": raw_sims.tolist(),
        "smoothed_similarities": smoothed.tolist(),
        "boundaries": boundaries,
        "window_times": [{"start": w.start_time, "end": w.end_time} for w in windows],
    }
    debug_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.info(f"Courbe de similarité sauvegardée : {debug_path}")

    if len(smoothed) == 0:
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(14, 5))
        x = list(range(len(raw_sims)))
        ax.plot(x, raw_sims, alpha=0.35, label="Similarité brute", color="steelblue")
        ax.plot(x, smoothed, linewidth=2, label="Lissée (gaussien)", color="darkorange")

        threshold = np.percentile(smoothed, 25)
        ax.axhline(y=threshold, color="red", linestyle="--", alpha=0.6, label="Seuil (percentile)")

        for b in boundaries:
            ax.axvline(x=b, color="red", alpha=0.4, linewidth=1.5)

        ax.set_xlabel("Fenêtre")
        ax.set_ylabel("Similarité cosine")
        ax.set_title("Détection des frontières de sujets")
        ax.legend(loc="lower left")
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)

        png_path = Path(output_path).with_suffix(".similarity.png")
        fig.tight_layout()
        fig.savefig(str(png_path), dpi=150)
        plt.close(fig)
        log.info(f"Graphique similarité sauvegardé : {png_path}")
    except ImportError:
        log.warning("matplotlib non installé — graphique PNG non généré")


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------
def run_pipeline(cfg: Config, parallel_slots: int = 1,
                 no_cache: bool = False,
                 participants: str | None = None,
                 entreprises: str | None = None) -> str:
    t_start = time.time()
    step_times: dict[str, float] = {}
    log.info(f"[PERF] RAM initiale = {ram_total_mb():.0f} Mo")
    log.info("=" * 60)
    log.info("Pipeline Meeting Minutes — Topic Boundary + Assemblage déterministe")
    log.info("=" * 60)

    # ── 0. Chargement ──
    t = time.time()
    if cfg.transcript_path:
        segments = load_segments_from_transcript(cfg.transcript_path)
    else:
        segments = load_segments(cfg.json_path)
    step_times["chargement"] = round(time.time() - t, 1)

    # ── 0b. Speaker mapping ──
    speaker_mapping: dict[str, dict] = {}
    if participants and cfg.transcript_path:
        t = time.time()
        start_llm_server_slots(cfg, 1)
        speaker_mapping = resolve_speaker_mapping(
            cfg.transcript_path, participants,
            entreprises or "", cfg,
        )
        segments = apply_speaker_mapping(segments, speaker_mapping)
        step_times["speaker_mapping"] = round(time.time() - t, 1)

    # ── 1. Fenêtres ──
    t = time.time()
    windows = build_windows(segments, cfg.boundary_window_size)
    step_times["fenetres_glissantes"] = round(time.time() - t, 1)

    # ── 2. Embeddings ──
    t = time.time()
    embeddings = embed_windows(windows, cfg.embedding_model, cfg.embedding_batch_size)
    step_times["embeddings"] = round(time.time() - t, 1)

    # ── 3. Frontières ──
    t = time.time()
    boundaries, raw_sims, smoothed = detect_topic_boundaries(
        embeddings,
        sigma=cfg.boundary_smoothing_sigma,
        percentile=cfg.boundary_percentile,
        min_distance=cfg.boundary_min_distance,
    )
    step_times["detection_frontieres"] = round(time.time() - t, 1)
    save_similarity_debug(raw_sims, smoothed, boundaries, windows, cfg.output_path)

    # ── 4. Chunks ──
    t = time.time()
    chunks = build_topic_chunks(segments, windows, boundaries, cfg.max_chunk_chars, cfg=cfg)
    step_times["construction_chunks"] = round(time.time() - t, 1)
    if not chunks:
        log.error("Aucun chunk créé.")
        sys.exit(1)

    actual_slots = len(chunks) if parallel_slots <= 0 else min(parallel_slots, len(chunks))
    mode_label = "sequential" if actual_slots == 1 else f"parallel-{actual_slots}"
    log.info(f"Mode LLM : {mode_label}")

    # ── 5. Sections JSON via LLM ──
    sections_cache = Path(cfg.output_path).with_suffix(".sections.json")
    start_llm_server_slots(cfg, actual_slots)

    sampler = RamSampler(interval=0.5)
    t = time.time()
    if sections_cache.exists() and not no_cache:
        log.info(f"Cache sections trouvé : {sections_cache}")
        sections = json.loads(sections_cache.read_text(encoding="utf-8"))
    else:
        sampler.start()
        if actual_slots == 1:
            sections = [generate_section_json(c, cfg) for c in chunks]
        else:
            with ThreadPoolExecutor(max_workers=actual_slots) as pool:
                results = list(pool.map(lambda c: generate_section_json(c, cfg), chunks))
            sections = results
        sampler.stop()
        sections_cache.write_text(
            json.dumps(sections, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info(f"Sections JSON sauvegardées : {sections_cache}")
    step_times["generation_sections_llm"] = round(time.time() - t, 1)

    sections.sort(key=lambda s: s.get("_start_time", 0))

    # ── 6. Executive Summary ──
    t = time.time()
    exec_summary = build_exec_summary(sections, cfg, transcript_path=cfg.transcript_path)
    step_times["executive_summary_llm"] = round(time.time() - t, 1)

    # ── 7. Plan d'attaque ──
    t = time.time()
    plan = build_plan_attack(sections, cfg)
    step_times["plan_attack_llm"] = round(time.time() - t, 1)

    # ── 8. Assemblage déterministe ──
    t = time.time()
    source = cfg.transcript_path or cfg.json_path
    final_report = assemble_report(sections, exec_summary, source,
                                    plan=plan,
                                    speaker_mapping=speaker_mapping)
    step_times["assemblage_deterministe"] = round(time.time() - t, 3)

    output = Path(cfg.output_path)
    output.write_text(final_report, encoding="utf-8")

    def _count_type(s: dict, t: str) -> int:
        return sum(1 for it in (s.get("plan") or []) if it.get("type") == t)

    n_engagements_total = sum(_count_type(s, "engagement") for s in sections)
    n_suggestions_total = sum(_count_type(s, "suggestion") for s in sections)
    assembly_debug = {
        "exec_summary": exec_summary,
        "n_sections": len(sections),
        "n_decisions_total": sum(len(s["decisions"]) for s in sections),
        "n_engagements_total": n_engagements_total,
        "n_suggestions_total": n_suggestions_total,
        "n_plan_items_total": len(plan),
        "plan_attack_mode": cfg.plan_attack_mode,
        "sections_summary": [
            {
                "chunk_id": s.get("_chunk_id"),
                "titre": s["titre"],
                "n_decisions": len(s["decisions"]),
                "n_engagements": _count_type(s, "engagement"),
                "n_suggestions": _count_type(s, "suggestion"),
                "start_time": s.get("_start_time"),
                "end_time": s.get("_end_time"),
            }
            for s in sections
        ],
    }
    assembly_path = output.with_suffix(".assembly.json")
    assembly_path.write_text(
        json.dumps(assembly_debug, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total = time.time() - t_start
    ram_process = ram_mb()
    ram_server = _server_ram_mb()
    ram_system = ram_total_mb()

    log.info("=" * 60)
    log.info(f"[PERF] TOTAL : {total:.1f}s ({total/60:.1f} min)")
    log.info(f"[PERF] Fichier : {output.resolve()}")
    log.info("=" * 60)

    # n_llm_calls : perchunk = 3 par chunk + 1 exec_summary ; legacy = 2 par
    # chunk + 1 exec_summary + 1 plan_attack
    per_chunk_calls = 3 if cfg.plan_attack_mode == "perchunk" else 2
    final_calls = 1 if cfg.plan_attack_mode == "perchunk" else 2
    metrics = {
        "pipeline": "meeting_minutes_pipeline.py",
        "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": Path(cfg.llm_model_path).name,
        "model_path": cfg.llm_model_path,
        "source": source,
        "total_duration_s": round(total, 1),
        "total_duration_min": round(total / 60, 2),
        "ram_process_mb": round(ram_process, 0),
        "ram_llama_server_mb": round(ram_server, 0),
        "ram_system_mb": round(ram_system, 0),
        "n_segments": len(segments),
        "n_chunks": len(chunks),
        "n_boundaries": len(boundaries),
        "n_decisions_total": assembly_debug["n_decisions_total"],
        "n_engagements_total": assembly_debug["n_engagements_total"],
        "n_suggestions_total": assembly_debug["n_suggestions_total"],
        "n_plan_items_total": assembly_debug["n_plan_items_total"],
        "n_llm_calls": len(chunks) * per_chunk_calls + final_calls,
        "n_llm_calls_per_chunk": per_chunk_calls,
        "plan_attack_mode": cfg.plan_attack_mode,
        "mode": mode_label,
        "parallel_slots": actual_slots,
        "ram_llama_server_peak_mb": round(sampler.peak_server(), 0),
        "ram_llama_server_avg_mb": round(sampler.avg_server(), 0),
        "ram_system_peak_mb": round(sampler.peak_system(), 0),
        "boundary_window_size": cfg.boundary_window_size,
        "boundary_smoothing_sigma": cfg.boundary_smoothing_sigma,
        "boundary_percentile": cfg.boundary_percentile,
        "boundary_min_distance": cfg.boundary_min_distance,
        "llm_n_ctx": cfg.llm_n_ctx,
        "llm_n_threads": cfg.llm_n_threads,
        "llm_temperature": cfg.llm_temperature,
        "step_times_s": step_times,
        "prompts": {
            "prompt_resume": PROMPT_RESUME,
            "prompt_extraction": PROMPT_EXTRACTION,
            "prompt_plan_attack": PROMPT_PLAN_ATTACK,
            "prompt_plan_perchunk": PROMPT_PLAN_PERCHUNK,
            "prompt_exec_summary": PROMPT_EXEC_SUMMARY,
        },
    }
    metrics_path = output.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"[PERF] Métriques : {metrics_path.resolve()}")

    return final_report


# ---------------------------------------------------------------------------
# Point d'entrée CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Meeting Minutes — Boundary Detection + Assemblage déterministe",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    _cfg = Config()
    parser.add_argument("--json",        default=_cfg.json_path)
    parser.add_argument("--transcript",  default=_cfg.transcript_path)
    parser.add_argument("--output",      default=_cfg.output_path)
    parser.add_argument("--model",       default=_cfg.llm_model_path,
        help="Chemin vers le modèle GGUF.")
    parser.add_argument("--server",      default=_cfg.llama_server_exe)
    parser.add_argument("--n-ctx",       type=int, default=_cfg.llm_n_ctx)
    parser.add_argument("--n-threads",   type=int, default=_cfg.llm_n_threads)
    parser.add_argument("--port",        type=int, default=_cfg.llm_server_port)
    parser.add_argument("--window-size",    type=int,   default=_cfg.boundary_window_size)
    parser.add_argument("--sigma",          type=float, default=_cfg.boundary_smoothing_sigma)
    parser.add_argument("--percentile",     type=float, default=_cfg.boundary_percentile)
    parser.add_argument("--min-distance",   type=int,   default=_cfg.boundary_min_distance)
    parser.add_argument("--max-chunk-chars", type=int,  default=_cfg.max_chunk_chars)
    parser.add_argument("--no-cache", action="store_true", help="Force la régénération des sections.")
    parser.add_argument("--participants", type=str, default=None,
                        help="Noms des participants séparés par virgule.")
    parser.add_argument("--entreprises", type=str, default=None,
                        help="Noms des entreprises impliquées.")
    parser.add_argument("--parallel-chunks", default="1",
        help="Nombre de chunks traités en parallèle. '1' = séquentiel "
             "(défaut, optimal sur CPU memory-bound — voir bench parallelisme). "
             "'auto' = tous simultanément. Sur CPU sans GPU, parallel >1 "
             "n'apporte pas de gain car la bande passante RAM sature.")
    parser.add_argument("--plan-attack-mode", choices=["perchunk", "legacy"],
        default=_cfg.plan_attack_mode,
        help="'perchunk' (défaut) : plan unifié (engagement + suggestion, "
             "cap 2 items/chunk) extrait par chunk pendant la réunion (+1 "
             "appel LLM par chunk avec HIT cache), plan final = assemblage "
             "déterministe sans LLM. 'legacy' : 1 appel LLM final sur les "
             "résumés agrégés.")

    args = parser.parse_args()

    if args.parallel_chunks.lower() == "auto":
        parallel_slots = -1
        slots_slug = "auto"
    else:
        parallel_slots = int(args.parallel_chunks)
        slots_slug = str(parallel_slots)

    resolved_model = args.model
    if not Path(resolved_model).exists():
        parser.error(f"Modèle introuvable : {resolved_model}")

    model_slug = Path(resolved_model).stem
    _default_output = _cfg.output_path
    if args.output == _default_output:
        transcript_slug = Path(args.transcript).stem if args.transcript else "json_source"
        run_slug = "seq" if slots_slug == "1" else f"par{slots_slug}"
        _results_dir = Path(__file__).parent / "results" / "meeting_minutes" / transcript_slug / model_slug / run_slug
        _results_dir.mkdir(parents=True, exist_ok=True)
        args.output = str(_results_dir / "compte_rendu.md")

    cfg = Config(
        json_path=args.json,
        transcript_path=args.transcript,
        output_path=args.output,
        llm_model_path=resolved_model,
        llama_server_exe=args.server,
        llm_n_ctx=args.n_ctx,
        llm_n_threads=args.n_threads,
        llm_server_port=args.port,
        boundary_window_size=args.window_size,
        boundary_smoothing_sigma=args.sigma,
        boundary_percentile=args.percentile,
        boundary_min_distance=args.min_distance,
        max_chunk_chars=args.max_chunk_chars,
        plan_attack_mode=args.plan_attack_mode,
    )

    run_pipeline(cfg, parallel_slots=parallel_slots,
                 no_cache=args.no_cache,
                 participants=args.participants,
                 entreprises=args.entreprises)
