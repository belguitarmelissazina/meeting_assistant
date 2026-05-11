"""
Pipeline LLM live : chunking sémantique append-safe + worker llama-server
consommant les chunks au fil de l'eau pendant la captation.

Composants :
  - TurnBuilder : mots ASR → turns (groupage par changement de locuteur
                  ou gap de silence > threshold)
  - StreamingTopicChunker : turns → windows → embeddings → détection de
                            frontières append-safe → chunks clos
  - LiveLLMWorker : démarre llama-server au record_start, consomme une file
                    de chunks clos, produit {résumé, décisions}
                    par chunk, puis à finalize() : exec summary +
                    plan d'attaque + assemble_report → compte_rendu.md

Append-safe vs algo batch :
  - lissage gaussien CAUSAL (onesided) au lieu de bilatéral
  - seuil LOCAL (moyenne + k·σ sur les N dernières similarités) au lieu
    de percentile global
  - confirmation avec DÉLAI : un creux candidat à t n'est confirmé comme
    frontière qu'après M fenêtres supplémentaires sans creux inférieur
    proche → maximum local garanti
"""
from __future__ import annotations

import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# TurnBuilder
# ══════════════════════════════════════════════════════════════════════════

SILENCE_GAP_S = 0.8         # gap > 0.8s entre 2 mots → fin de turn
MIN_TURN_DURATION_S = 5     # ne flush aux frontières de phrase qu'au bout de 5s
MAX_TURN_DURATION_S = 30    # garde-fou absolu si aucune phrase ne se termine
MAX_TURN_WORDS = 120        # garde-fou absolu en nb de mots
SENTENCE_ENDERS = (".", "!", "?", "…")


@dataclass
class Turn:
    start: float
    end: float
    speaker: str
    text: str


def split_turn_sentences(turn: "Turn", max_chars: int | None = 300) -> list["Turn"]:
    """Découpe une turn en sous-turns au niveau phrase, comme le fait
    normalize_transcript.py pour le batch. Ça aligne la granularité du
    chunker sur celle de la pipeline offline : fenêtres de 3 phrases au
    lieu de 3 turns potentiellement longues, embeddings MiniLM plus
    représentatifs d'un sujet cohérent.

    Les timestamps des sous-turns sont répartis proportionnellement à la
    longueur de chaque phrase — approximatifs mais sans impact sur la
    qualité du chunking (qui n'utilise pas les timestamps).
    """
    try:
        from normalize_transcript import split_sentences
    except ImportError:
        return [turn]
    sentences = split_sentences(turn.text, max_chars=max_chars)
    if len(sentences) <= 1:
        return [turn]
    total_len = sum(len(s) for s in sentences)
    if total_len == 0:
        return [turn]
    duration = max(0.0, turn.end - turn.start)
    out: list[Turn] = []
    cursor = turn.start
    for s in sentences:
        frac = len(s) / total_len
        s_end = cursor + duration * frac
        out.append(Turn(
            start=cursor,
            end=s_end if duration > 0 else turn.end,
            speaker=turn.speaker,
            text=s,
        ))
        cursor = s_end
    # Garantie que la dernière sous-turn finit exactement à turn.end.
    if out:
        out[-1] = Turn(
            start=out[-1].start,
            end=turn.end,
            speaker=out[-1].speaker,
            text=out[-1].text,
        )
    return out


class TurnBuilder:
    """Accumule les mots et émet des turns sur :
      - changement de locuteur
      - silence > silence_gap_s entre 2 mots
      - durée cumulée > max_turn_duration_s (flush forcé)
      - nb de mots accumulés > max_turn_words  (flush forcé)

    Les deux derniers critères sont critiques en phase pré-bootstrap
    diarisation, où tous les mots ont `SPEAKER_?` et où l'ASR streaming
    produit des mots quasi sans interruption. Sans flush forcé, les turns
    s'accumulent indéfiniment et rien ne sort vers le chunker.
    """

    def __init__(
        self,
        silence_gap_s: float = SILENCE_GAP_S,
        min_turn_duration_s: float = MIN_TURN_DURATION_S,
        max_turn_duration_s: float = MAX_TURN_DURATION_S,
        max_turn_words: int = MAX_TURN_WORDS,
    ) -> None:
        self.silence_gap = silence_gap_s
        self.min_turn_duration = min_turn_duration_s
        self.max_turn_duration = max_turn_duration_s
        self.max_turn_words = max_turn_words
        self._buffer_words: list[dict] = []
        self._buffer_speaker: str | None = None
        self._pending_turns: list[Turn] = []

    def add_word(self, word: dict) -> None:
        """word: {word: str, start: float, end: float, speaker: str}

        Règles de flush, dans l'ordre de priorité :
          1. Changement de locuteur OU silence > gap → flush immédiat
             (limites naturelles de conversation)
          2. Mot avec ponctuation finale . ! ? … ET buffer ≥ min_duration
             → flush à une frontière de PHRASE (aligne sur le batch)
          3. Garde-fous : buffer > max_duration OU > max_words → flush
             forcé (rare, se déclenche si l'ASR tourne en continu sans
             jamais produire de ponctuation terminale pendant 30s)
        """
        spk = word.get("speaker", "SPEAKER_?")
        if not self._buffer_words:
            self._buffer_speaker = spk
            self._buffer_words.append(word)
            return

        prev_end = self._buffer_words[-1]["end"]
        gap = word["start"] - prev_end
        buffer_start = self._buffer_words[0]["start"]
        buffer_duration_before = prev_end - buffer_start

        # Règle 1 : locuteur ou silence → flush avant d'ajouter le mot
        if spk != self._buffer_speaker or gap > self.silence_gap:
            self._flush()
            self._buffer_speaker = spk
            self._buffer_words.append(word)
            return

        # On ajoute le mot courant avant de regarder s'il conclut une phrase
        self._buffer_words.append(word)
        buffer_duration_after = word["end"] - buffer_start

        # Règle 2 : fin de phrase + contenu suffisant → flush propre
        w_str = str(word.get("word", "")).rstrip()
        if (w_str.endswith(SENTENCE_ENDERS)
                and buffer_duration_after >= self.min_turn_duration):
            self._flush()
            return

        # Règle 3 : garde-fou absolu (ASR qui n'a pas sorti de . ! ? depuis
        # très longtemps, typique pré-bootstrap avec speech continu)
        if (buffer_duration_after >= self.max_turn_duration
                or len(self._buffer_words) >= self.max_turn_words):
            self._flush()

    def _flush(self) -> None:
        if not self._buffer_words:
            return
        text = " ".join(w["word"] for w in self._buffer_words).strip()
        if text:
            turn = Turn(
                start=self._buffer_words[0]["start"],
                end=self._buffer_words[-1]["end"],
                speaker=self._buffer_speaker or "SPEAKER_?",
                text=text,
            )
            self._pending_turns.append(turn)
            logger.info(
                "[LIVE][TURNS] Turn émise : [%s] %.1fs–%.1fs, %d mots, %d chars",
                turn.speaker, turn.start, turn.end,
                len(self._buffer_words), len(text),
            )
        self._buffer_words = []

    def drain(self) -> list[Turn]:
        """Récupère les turns clos depuis le dernier drain."""
        out = self._pending_turns
        self._pending_turns = []
        return out

    def finalize(self) -> list[Turn]:
        """Vide le buffer interne (dernière turn en cours) puis drain."""
        self._flush()
        return self.drain()


# ══════════════════════════════════════════════════════════════════════════
# StreamingTopicChunker
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class ClosedChunk:
    chunk_id: int
    start_time: float
    end_time: float
    turns: list[Turn]
    text: str
    segments: list[dict] = field(default_factory=list)  # pour build_plan_attack

    def as_segments(self) -> list[dict]:
        return [
            {"start": t.start, "end": t.end, "speaker": t.speaker, "text": t.text}
            for t in self.turns
        ]


class StreamingTopicChunker:
    """Chunker sémantique append-safe.

    Usage :
        chunker = StreamingTopicChunker(on_chunk_closed=lambda c: ...)
        for turn in turns:
            chunker.add_turn(turn)
        chunker.finalize()  # ferme le dernier chunk

    Paramètres clés :
      - window_size : nb de turns concaténés par fenêtre d'embedding
      - smoothing_sigma : écart-type du lissage gaussien causal
      - rolling_n : taille de la fenêtre glissante pour le seuil local
      - k_sigma : seuil = mean - k_sigma * std des similarités récentes
      - confirm_delay : nb de fenêtres à attendre après un creux candidat
                         avant de le confirmer comme frontière
      - min_chunk_turns : taille min d'un chunk (en turns) pour filtrer
                          les boundary false positives
      - max_chunk_chars : taille max d'un chunk en chars. Au-delà, commit
                          forcé pour éviter qu'un chunk monothématique
                          n'attende `finalize()` et bloque la pipeline LLM.
                          Si on a un candidat sémantique en attente de
                          confirmation, on commit à la vallée la plus
                          profonde plutôt qu'au turn courant (équivalent
                          du re-split sémantique batch).
    """

    def __init__(
        self,
        on_chunk_closed=None,
        window_size: int = 3,
        # smoothing_sigma 2.0 (= batch) : lissage causal sur les 5
        # dernières similarités pour filtrer les fluctuations courtes.
        smoothing_sigma: float = 2.0,
        rolling_n: int = 20,
        # k_sigma 2.0 : seuil = mean - 2σ → seules les vraies vallées
        # franches passent (vs 1.5 trop sensible aux micro-variations).
        k_sigma: float = 2.0,
        # confirm_delay 5 : on attend 5 fenêtres après un candidat avant
        # de le confirmer comme frontière → plus de stabilité.
        confirm_delay: int = 5,
        # min_chunk_turns 10 : empêche les chunks ultra-courts (< 10
        # turns ≈ < 1 min de discussion) qui n'ont pas de matière LLM.
        min_chunk_turns: int = 10,
        max_chunk_chars: int = 15000,
        embed_model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.on_chunk_closed = on_chunk_closed
        self.window_size = window_size
        self.smoothing_sigma = smoothing_sigma
        self.rolling_n = rolling_n
        self.k_sigma = k_sigma
        self.confirm_delay = confirm_delay
        self.min_chunk_turns = min_chunk_turns
        self.max_chunk_chars = max_chunk_chars

        self._turns: list[Turn] = []
        self._embeddings: list[np.ndarray] = []  # 1 par fenêtre
        self._similarities: list[float] = []     # s[i] entre w[i] et w[i+1]
        self._smoothed: list[float] = []
        self._candidate_boundaries: list[tuple[int, float]] = []  # (idx, smoothed_sim)
        self._last_committed_boundary: int = -1  # index de la dernière frontière (dans turns)
        self._emitted_chunk_id: int = 0
        self._model = None
        self._embed_model_name = embed_model_name

    def preload(self) -> None:
        """Charge SentenceTransformer en avance. Appeler avant la captation
        pour que le premier embedding ne bloque pas."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                import os
                name = self._embed_model_name
                minilm_dir = os.environ.get("MINILM_DIR")
                if (minilm_dir and name == "all-MiniLM-L6-v2"
                        and Path(minilm_dir).is_dir()):
                    name = minilm_dir
                self._model = SentenceTransformer(name, device="cpu")
                # Warm-up
                self._model.encode(["warm"], convert_to_numpy=True,
                                    normalize_embeddings=True)
                logger.info("StreamingTopicChunker : MiniLM préchargé")
            except Exception as exc:
                logger.exception("Préchargement embedding a échoué : %s", exc)
                self._model = None

    # ── Ingestion ──────────────────────────────────────────────────────────
    def add_turn(self, turn: Turn) -> None:
        self._turns.append(turn)
        # Peut-on former une nouvelle fenêtre ?
        if len(self._turns) - self._last_committed_boundary - 1 >= self.window_size:
            self._rebuild_from(self._last_committed_boundary + 1)
        # Garde-fou taille : si le chunk en cours dépasse max_chunk_chars,
        # on force un commit. Préfère un candidat sémantique en attente
        # (vallée la plus profonde) ; à défaut, coupe au turn courant.
        self._enforce_size_cap()

    def _current_chunk_chars(self) -> int:
        """Nb de chars du chunk en cours (depuis la dernière frontière)."""
        start = self._last_committed_boundary + 1
        if start >= len(self._turns):
            return 0
        return sum(
            len(t.text) + len(t.speaker) + 4  # "[spk]: " + "\n"
            for t in self._turns[start:]
        )

    def _enforce_size_cap(self) -> None:
        if self._current_chunk_chars() < self.max_chunk_chars:
            return
        # Choisit la meilleure frontière dispo : candidat avec la similarité
        # lissée la plus basse (vallée la plus profonde), à condition qu'il
        # produise un chunk d'au moins min_chunk_turns. Sinon coupe au turn
        # courant pour ne pas dépasser indéfiniment.
        best_idx: int | None = None
        best_sim = float("inf")
        for cand_turn, cand_sim in self._candidate_boundaries:
            if (cand_sim < best_sim
                    and self._segments_between(cand_turn) >= self.min_chunk_turns):
                best_idx, best_sim = cand_turn, cand_sim
        if best_idx is None:
            best_idx = len(self._turns) - 1
            logger.info(
                "[LIVE][CHUNKER] ⚠ Garde-fou taille (%d chars) : commit "
                "forcé au turn courant #%d (aucun candidat sémantique)",
                self._current_chunk_chars(), best_idx,
            )
        else:
            logger.info(
                "[LIVE][CHUNKER] ⚠ Garde-fou taille (%d chars) : commit "
                "à la vallée sémantique la plus profonde turn=#%d (sim=%.3f)",
                self._current_chunk_chars(), best_idx, best_sim,
            )
        self._commit_boundary(best_idx)

    def finalize(self) -> None:
        """Ferme le dernier chunk en cours et le publie (s'il y a de la matière)."""
        # Commit des candidats restants s'ils sont dans la fenêtre de
        # confirmation (délai dépassé puisqu'on ferme).
        while self._candidate_boundaries:
            idx, _ = self._candidate_boundaries.pop(0)
            if self._segments_between(idx) >= self.min_chunk_turns:
                self._commit_boundary(idx)
        # Dernier chunk : tout ce qui reste après la dernière frontière.
        if len(self._turns) - self._last_committed_boundary - 1 > 0:
            self._commit_boundary(len(self._turns) - 1, is_final=True)

    # ── Internal ───────────────────────────────────────────────────────────
    def _rebuild_from(self, start_turn_idx: int) -> None:
        """(Re)construit les fenêtres/embeddings à partir de start_turn_idx.

        Append-safe : on ne recalcule que les nouvelles fenêtres depuis la
        dernière frontière committée. Les lissages antérieurs ne sont pas
        modifiés — c'est la garantie causale.
        """
        if self._model is None:
            self.preload()
            if self._model is None:
                return  # pas de modèle → on ne chunk pas

        # Fenêtres depuis start_turn_idx (chaque fenêtre = window_size turns
        # consécutifs)
        # On ne rebuild que les fenêtres NOUVELLES depuis le dernier embedding.
        n_turns = len(self._turns)
        n_windows_existing = len(self._embeddings)
        # Fenêtre i commence au turn (start_turn_idx + i) et couvre
        # window_size turns.
        max_window_idx = n_turns - start_turn_idx - self.window_size
        if max_window_idx < 0:
            return

        # On ne rebuild que les fenêtres non encore embeddées.
        for i in range(n_windows_existing, max_window_idx + 1):
            turns_chunk = self._turns[start_turn_idx + i :
                                       start_turn_idx + i + self.window_size]
            text = "\n".join(f"[{t.speaker}]: {t.text}" for t in turns_chunk
                              if t.text.strip())
            if not text:
                # Fenêtre vide : duplique l'embedding précédent pour garder
                # l'indexation.
                if self._embeddings:
                    self._embeddings.append(self._embeddings[-1].copy())
                else:
                    # Cas limite : toute 1ère fenêtre vide (improbable)
                    self._embeddings.append(np.zeros(384, dtype=np.float32))
                continue
            emb = self._model.encode(
                [text], convert_to_numpy=True, normalize_embeddings=True,
            )[0]
            self._embeddings.append(emb.astype(np.float32))

            # Nouvelle similarité (entre la nouvelle fenêtre et la précédente).
            if len(self._embeddings) >= 2:
                sim = float(np.dot(self._embeddings[-2], self._embeddings[-1]))
                self._similarities.append(sim)
                self._update_smoothed()
                self._detect_candidate()

        self._maybe_confirm()

    def _update_smoothed(self) -> None:
        """Lissage gaussien CAUSAL sur la dernière similarité ajoutée."""
        if self.smoothing_sigma <= 0 or len(self._similarities) <= 2:
            self._smoothed.append(self._similarities[-1])
            return
        # Noyau causal one-sided : on fenêtre les 2*sigma dernières valeurs
        # et on applique les poids gaussiens (queue inclus uniquement).
        sigma = self.smoothing_sigma
        window_n = min(int(2 * sigma) + 1, len(self._similarities))
        vals = np.array(self._similarities[-window_n:])
        # Poids : gaussienne centrée sur le dernier point (i=window_n-1).
        positions = np.arange(window_n) - (window_n - 1)
        weights = np.exp(-0.5 * (positions / sigma) ** 2)
        weights /= weights.sum()
        self._smoothed.append(float(np.sum(vals * weights)))

    def _detect_candidate(self) -> None:
        """Ajoute un candidat de frontière si la dernière similarité lissée
        est significativement basse par rapport au seuil local."""
        n = len(self._smoothed)
        if n < self.rolling_n:
            return  # pas assez d'historique pour un seuil fiable
        recent = np.array(self._smoothed[-self.rolling_n:])
        mean = float(recent.mean())
        std = float(recent.std())
        threshold = mean - self.k_sigma * std
        last = self._smoothed[-1]
        if last < threshold:
            # Index de la fenêtre dont la similarité "sortante" est basse :
            # similarity[i] = sim(window[i], window[i+1]) → la frontière est
            # à window[i+1], donc le turn pivot est
            # start_turn_idx + (i+1). Pour un chunker on_the_fly, on note
            # l'index du turn à cet endroit.
            # ici self._similarities[n-1] correspond à window_index = n.
            window_idx = len(self._similarities)  # window[n-1] vs window[n]
            turn_pivot = (self._last_committed_boundary + 1) + window_idx
            self._candidate_boundaries.append((turn_pivot, last))
            logger.debug("Candidat frontière à turn=%d (sim=%.3f, seuil=%.3f)",
                         turn_pivot, last, threshold)

    def _maybe_confirm(self) -> None:
        """Confirme les candidats assez anciens pour avoir vu M fenêtres
        supplémentaires sans creux inférieur proche → maximum local."""
        n_windows = len(self._smoothed)
        confirmed: list[tuple[int, float]] = []
        remaining: list[tuple[int, float]] = []
        for cand_turn, cand_sim in self._candidate_boundaries:
            # Combien de fenêtres depuis le candidat ?
            cand_window_idx = cand_turn - (self._last_committed_boundary + 1)
            delay = n_windows - cand_window_idx
            if delay < self.confirm_delay:
                remaining.append((cand_turn, cand_sim))
                continue
            # Est-ce le min local dans les confirm_delay fenêtres suivantes ?
            local_min = True
            end = min(cand_window_idx + self.confirm_delay, len(self._smoothed))
            for j in range(cand_window_idx + 1, end):
                if self._smoothed[j] < cand_sim:
                    local_min = False
                    break
            if local_min and self._segments_between(cand_turn) >= self.min_chunk_turns:
                confirmed.append((cand_turn, cand_sim))
            # Si pas local min ou chunk trop petit : on abandonne ce candidat.
        self._candidate_boundaries = remaining

        for turn_idx, sim in confirmed:
            logger.info("[LIVE][CHUNKER] → Frontière sémantique confirmée "
                        "(turn #%d, similarité lissée=%.3f vs seuil local)",
                        turn_idx, sim)
            self._commit_boundary(turn_idx)

    def _segments_between(self, turn_end_idx: int) -> int:
        """Nombre de turns dans le chunk qui se fermerait à turn_end_idx."""
        return turn_end_idx - self._last_committed_boundary

    def _commit_boundary(self, turn_end_idx: int, *, is_final: bool = False) -> None:
        """Ferme le chunk qui va du dernier boundary jusqu'à turn_end_idx
        (inclus), l'émet via callback, puis redémarre les buffers."""
        start_idx = self._last_committed_boundary + 1
        chunk_turns = self._turns[start_idx:turn_end_idx + 1]
        if not chunk_turns:
            return
        chunk = ClosedChunk(
            chunk_id=self._emitted_chunk_id,
            start_time=chunk_turns[0].start,
            end_time=chunk_turns[-1].end,
            turns=chunk_turns,
            text="\n".join(f"[{t.speaker}]: {t.text}" for t in chunk_turns),
        )
        chunk.segments = chunk.as_segments()
        self._emitted_chunk_id += 1
        self._last_committed_boundary = turn_end_idx

        # Reset des embeddings/similarités/smoothed — on les reconstruit
        # depuis la nouvelle frontière au prochain add_turn.
        self._embeddings = []
        self._similarities = []
        self._smoothed = []
        self._candidate_boundaries = []

        if self.on_chunk_closed is not None:
            try:
                self.on_chunk_closed(chunk)
            except Exception:
                logger.exception("on_chunk_closed a levé")


# ══════════════════════════════════════════════════════════════════════════
# LiveLLMWorker
# ══════════════════════════════════════════════════════════════════════════

class LiveLLMWorker:
    """Consomme les chunks clos émis par le chunker et les passe au LLM
    (llama-server local) au fil de l'eau. Résultats accumulés en mémoire.

    À finalize() : exec summary + plan d'attaque + assemble → markdown.
    """

    def __init__(self, out_dir: Path, context: dict | None = None,
                 parallel_slots: int = 2) -> None:
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.context = context or {}
        self._parallel_slots = max(1, parallel_slots)
        self._q: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._sections: list[dict] = []
        self._sections_lock = threading.Lock()
        self._started = False
        self._error: str | None = None
        self._cfg = None  # meeting_minutes_pipeline.Config
        # Stats parallélisation : permettent de vérifier dans traitement.md
        # que les slots sont vraiment utilisés en simultané.
        self._concurrent_count = 0
        self._max_concurrent = 0
        self._total_processed = 0
        self._concurrent_lock = threading.Lock()

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def n_sections(self) -> int:
        with self._sections_lock:
            return len(self._sections)

    def start(self) -> None:
        if self._started:
            return
        try:
            # Lazy import pour ne pas charger toute la pipeline LLM sauf
            # si on est vraiment en mode live.
            import meeting_minutes_pipeline as mmp
            self._mmp = mmp
            self._cfg = mmp.Config()
            # Prépare env vars pour le system prompt.
            import os
            os.environ["MEETING_CONTEXT"] = (self.context.get("contexte") or "")
            os.environ["MEETING_PARTICIPANTS"] = (self.context.get("participants") or "")
            os.environ["MEETING_ENTREPRISES"] = (self.context.get("entreprises") or "")
            # ctx total constant côté llama-server : N slots se partagent
            # le pool KV → pas de surcoût RAM, juste du débit en plus.
            mmp.start_llm_server_slots(self._cfg,
                                       parallel_slots=self._parallel_slots)
        except Exception as exc:
            self._error = f"Init LiveLLMWorker: {exc}"
            logger.exception("Init LLM worker a échoué")
            return

        self._started = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="live-llm")
        self._thread.start()
        logger.info("[LIVE][LLM] Worker prêt — llama-server actif (%d slots), "
                    "en attente de chunks fermés par le chunker",
                    self._parallel_slots)

    def enqueue(self, chunk: ClosedChunk) -> None:
        if not self._started or self._error:
            return
        self._q.put(chunk)

    def finalize(self) -> str | None:
        """Vide la file, génère exec summary + plan d'attaque, écrit
        compte_rendu.md (+ docx). Renvoie le markdown ou None si échec."""
        if not self._started:
            return None
        q_left = self._q.qsize()
        if q_left > 0:
            logger.info("[LIVE][LLM] Drain de la file : %d chunks à traiter "
                        "avant assemblage", q_left)
        self._q.put(None)
        if self._thread:
            self._thread.join(timeout=600.0)

        if self._error:
            logger.warning("[LIVE][LLM] Erreur worker : %s", self._error)
            return None

        try:
            with self._sections_lock:
                # Tri par start_time : avec le pool, les sections terminent
                # potentiellement dans le désordre et exec_summary/plan_attack
                # attendent un ordre chronologique.
                sections = sorted(list(self._sections),
                                  key=lambda s: s.get("_start_time", 0))
            # Récap explicite pour vérifier dans traitement.md que la
            # parallélisation a bien fonctionné en pratique.
            with self._concurrent_lock:
                max_obs = self._max_concurrent
                total = self._total_processed
            if max_obs >= 2:
                verdict = (f"✅ PARALLÉLISATION ACTIVE "
                           f"(max {max_obs} chunks simultanés observés)")
            elif total > 1:
                verdict = ("⚠ Parallélisation NON observée : chunks "
                           "trop espacés pour se chevaucher (le pool a "
                           "fonctionné mais les chunks sont arrivés un par un)")
            else:
                verdict = ("ℹ Trop peu de chunks pour évaluer la "
                           "parallélisation")
            logger.info(
                "[LIVE][LLM] === RÉCAP PARALLÉLISATION === "
                "%d slots configurés, %d chunks traités au total, %s",
                self._parallel_slots, total, verdict,
            )
            if not sections:
                logger.warning("[LIVE][LLM] Aucune section produite — pas de "
                               "compte rendu généré")
                return None
            mmp = self._mmp
            import time as _time
            t_finalize = _time.time()
            logger.info("[LIVE][LLM] %d sections triées — lancement "
                        "exec_summary || plan_attack en parallèle "
                        "sur 2 slots llama-server", len(sections))
            # Les deux appels sont indépendants (ne lisent que `sections`)
            # → on les lance simultanément sur 2 slots llama-server.
            with ThreadPoolExecutor(max_workers=2,
                                     thread_name_prefix="live-finalize") as pool:
                f_exec = pool.submit(mmp.build_exec_summary, sections,
                                      self._cfg, transcript_path=None)
                f_plan = pool.submit(mmp.build_plan_attack, sections, self._cfg)
                exec_summary = f_exec.result()
                plan = f_plan.result()
            logger.info(
                "[LIVE][LLM] ✓ Exec summary + plan d'attaque terminés en "
                "%.1fs (parallèle, vs ~2× sériel) — %d items plan — "
                "assemblage markdown…",
                _time.time() - t_finalize, len(plan),
            )
            source = str(self.out_dir / "transcript.txt")
            md = mmp.assemble_report(sections, exec_summary, source,
                                     plan=plan, speaker_mapping=None)
            out_md = self.out_dir / "compte_rendu.md"
            out_md.write_text(md, encoding="utf-8")
            logger.info("[LIVE][LLM] ✓ compte_rendu.md écrit : %s "
                        "(%d sections, %d chars)",
                        out_md, len(sections), len(md))
            return md
        except Exception as exc:
            self._error = f"Finalize: {exc}"
            logger.exception("[LIVE][LLM] Finalize a levé")
            return None
        finally:
            # Toujours arrêter llama-server.
            try:
                self._mmp._kill_server()
            except Exception:
                pass

    def _loop(self) -> None:
        """Dispatcher : sort les chunks de la file et les soumet au pool de
        slots. Chaque chunk traité concurremment sur un slot llama-server
        libre. Les sections peuvent terminer dans le désordre — finalize()
        les retrie par start_time avant exec_summary/plan_attack."""
        pool = ThreadPoolExecutor(max_workers=self._parallel_slots,
                                   thread_name_prefix="live-llm-slot")
        in_flight: list = []
        try:
            while True:
                chunk = self._q.get()
                if chunk is None:
                    break
                in_flight.append(pool.submit(self._process_chunk, chunk))
                # Garbage collect les futures terminées pour éviter une
                # liste qui gonfle indéfiniment.
                in_flight = [f for f in in_flight if not f.done()]
            # Sentinel reçue : attend que tous les chunks en vol finissent.
            for f in in_flight:
                try:
                    f.result()
                except Exception:
                    pass  # déjà loggué dans _process_chunk
        finally:
            pool.shutdown(wait=True)

    def _process_chunk(self, chunk: "ClosedChunk") -> None:
        """Exécuté sur un slot du pool. Une exception ici ne doit pas
        bloquer les autres slots — on logge et on continue."""
        mmp = self._mmp
        slot = threading.current_thread().name
        # Tracking parallélisme : on incrémente avant le LLM call, on log
        # combien de chunks sont actuellement en vol simultanément, puis on
        # décrémente dans le finally.
        with self._concurrent_lock:
            self._concurrent_count += 1
            self._max_concurrent = max(self._max_concurrent,
                                        self._concurrent_count)
            current_concurrent = self._concurrent_count
            max_seen = self._max_concurrent
        try:
            import time as _time
            t0 = _time.time()
            topic = mmp.TopicChunk(
                chunk_id=chunk.chunk_id,
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                segments=chunk.segments,
                text=chunk.text,
            )
            parallel_indicator = (
                f"⚡ EN PARALLÈLE ({current_concurrent} chunks en vol)"
                if current_concurrent > 1
                else "🟡 SEUL EN VOL"
            )
            logger.info(
                "[LIVE][LLM] 🤖 [%s] Chunk #%d en traitement (%d chars) "
                "— %s, max observé=%d",
                slot, chunk.chunk_id, len(chunk.text),
                parallel_indicator, max_seen,
            )
            section = mmp.generate_section_json(topic, self._cfg)
            with self._sections_lock:
                self._sections.append(section)
            n_dec = len(section.get("decisions") or [])
            titre = section.get("titre", "?")
            logger.info("[LIVE][LLM] ✓ [%s] Chunk #%d traité en %.1fs : "
                        "titre='%s', %d décisions",
                        slot, chunk.chunk_id, _time.time() - t0, titre, n_dec)
        except Exception:
            logger.exception("Traitement LLM du chunk %d a échoué",
                             chunk.chunk_id)
        finally:
            with self._concurrent_lock:
                self._concurrent_count -= 1
                self._total_processed += 1
