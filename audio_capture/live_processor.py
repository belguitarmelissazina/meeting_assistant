"""
Pipeline live : ASR + VAD + embeddings + clustering online, nourri en PCM
temps réel via .push(chunk). À l'appel de .finalize(out_dir), écrit un
transcript.txt au même format que le pipeline batch, utilisable directement
par normalize_transcript.py.

Architecture :

    AudioRecorder (callback) → LiveProcessor.push(chunk)
                                         │
                            ┌────────────┴────────────┐
                            ▼                         ▼
                     ASR thread                 Embed thread
                (sherpa-onnx stream)       (silero VAD + resnet34)
                            │                         │
                            ▼                         ▼
                     list[words]         BootstrapOnlineClusterer
                                                      │
                                                      ▼
                                              list[(t, speaker)]

    .finalize(out_dir) : join, aligne mots ↔ speakers, écrit transcript.txt

Si le pipeline échoue pendant la captation (self._error set), .finalize()
n'écrit RIEN — le backend détecte l'absence de transcript.txt et retombe
sur la pipeline batch.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
EMBED_WIN_S = 1.2
EMBED_HOP_S = 0.6
EMBED_WIN_SAMPLES = int(EMBED_WIN_S * SAMPLE_RATE)
EMBED_HOP_SAMPLES = int(EMBED_HOP_S * SAMPLE_RATE)
VAD_CHUNK_SAMPLES = 512  # silero-vad préfère des chunks de 512 échantillons
BOOTSTRAP_SIZE = 1000    # ≈ 10 min à hop 0.6s


class LiveProcessor:
    """Consomme des chunks PCM, produit un transcript aligné sur locuteurs."""

    def __init__(self, enable_live_llm: bool = False) -> None:
        # Queues bornées : ~15 min d'audio max à 16kHz/1024 échantillons =
        # 14000 chunks. Au-delà, on drop (= start() est cassé depuis
        # longtemps, pas la peine d'accumuler).
        self._asr_q: queue.Queue = queue.Queue(maxsize=15000)
        self._embed_q: queue.Queue = queue.Queue(maxsize=15000)
        # _running = True dès la création : push() accepte les chunks
        # immédiatement. Ils s'empilent dans les queues, les workers les
        # consommeront quand start() aura fini le chargement des modèles.
        self._running = True
        self._started = False
        self._error: str | None = None
        self._threads: list[threading.Thread] = []
        # ASR state
        self._asr_words: list[dict] = []
        self._asr_words_lock = threading.Lock()
        # Embedding state
        self._embedding_times: list[float] = []   # center time of each window
        self._embedding_vecs: list[np.ndarray] = []
        # Clustering
        self._clusterer = None
        # Models préchargés dans .start() pour éviter de perdre les premières
        # fenêtres le temps du premier appel (lazy load torch/onnx = ~1-3 s).
        self._extractor = None
        self._vad_model = None
        # Live LLM (optionnel — activé seulement si le user le demande).
        self._enable_live_llm = enable_live_llm
        self._llm_context: dict = {}
        self._turn_builder = None
        self._chunker = None
        self._llm_worker = None

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def started(self) -> bool:
        return self._started

    def set_llm_context(self, context: dict) -> None:
        """À appeler avant start() si on veut activer le LLM live avec un
        contexte (participants, entreprises, contexte). Le worker LLM utilise
        ce contexte pour son system prompt."""
        self._llm_context = context or {}

    # ── API publique ──────────────────────────────────────────────────────
    def start(self) -> None:
        """Démarre les workers. Thread-safe tant qu'appelé une seule fois."""
        if self._started:
            return
        t_start = time.time()
        logger.info("[LIVE] Chargement des modèles… (les chunks audio s'empilent "
                    "en attendant)")
        try:
            from diar_pipeline.clustering import BootstrapOnlineClusterer
            from diar_pipeline.embeddings import _EmbeddingExtractor
            self._clusterer = BootstrapOnlineClusterer(bootstrap_size=BOOTSTRAP_SIZE)
            logger.info("[LIVE] Clusterer bootstrap+online instancié (bootstrap "
                        "size = %d embeddings ≈ 10 min)", BOOTSTRAP_SIZE)
            t0 = time.time()
            self._extractor = _EmbeddingExtractor("resnet34")
            warmup = np.zeros(EMBED_WIN_SAMPLES, dtype=np.float32)
            warmup[0] = 1e-6
            try:
                self._extractor.extract_from_array(warmup, SAMPLE_RATE)
            except Exception:
                pass
            logger.info("[LIVE] Extractor resnet34 chargé + warmup (%.1fs)",
                        time.time() - t0)
        except Exception as exc:
            self._error = f"Init clusterer/extractor: {exc}"
            self._running = False
            logger.exception("[LIVE] Init clusterer/extractor ÉCHOUÉ")
            return

        try:
            t0 = time.time()
            from silero_vad import load_silero_vad
            self._vad_model = load_silero_vad()
            import torch
            self._vad_model(torch.zeros(VAD_CHUNK_SAMPLES), SAMPLE_RATE)
            logger.info("[LIVE] VAD silero chargé + warmup (%.1fs)",
                        time.time() - t0)
        except Exception as exc:
            logger.warning("[LIVE] silero-vad indisponible (%s) — fallback RMS", exc)
            self._vad_model = None

        if self._enable_live_llm:
            try:
                t0 = time.time()
                from .live_llm import (
                    TurnBuilder, StreamingTopicChunker, LiveLLMWorker,
                )
                self._turn_builder = TurnBuilder()
                import tempfile as _tf
                tmp_out = Path(_tf.mkdtemp(prefix="live_llm_"))
                self._llm_worker = LiveLLMWorker(tmp_out, context=self._llm_context)
                self._llm_worker.start()
                if self._llm_worker.error:
                    logger.warning("[LIVE] LLM worker KO (%s) — désactivation LLM "
                                   "live, transcript live reste actif",
                                   self._llm_worker.error)
                    self._llm_worker = None
                if self._llm_worker is not None:
                    self._chunker = StreamingTopicChunker(
                        on_chunk_closed=self._on_chunk_closed,
                    )
                    self._chunker.preload()
                    logger.info("[LIVE] LLM worker + chunker MiniLM prêts "
                                "(llama-server démarré, %.1fs)", time.time() - t0)
            except Exception as exc:
                logger.warning("[LIVE] Init chunker/LLM worker KO (%s) — "
                               "fallback batch au stop", exc)
                self._turn_builder = None
                self._chunker = None
                self._llm_worker = None

        t_asr = threading.Thread(target=self._asr_worker, daemon=True, name="live-asr")
        t_emb = threading.Thread(target=self._embed_worker, daemon=True, name="live-embed")
        t_asr.start()
        t_emb.start()
        self._threads = [t_asr, t_emb]
        if self._llm_worker is not None:
            t_turn = threading.Thread(target=self._turn_dispatch_worker,
                                       daemon=True, name="live-turns")
            t_turn.start()
            self._threads.append(t_turn)
        self._started = True
        live_llm_status = "ON" if self._llm_worker is not None else "OFF"
        logger.info(
            "[LIVE] ✓ Pipeline live prête en %.1fs — ASR + embeddings + "
            "VAD=%s + LLM=%s. La file contient %d chunks audio en attente.",
            time.time() - t_start,
            "silero" if self._vad_model is not None else "RMS",
            live_llm_status,
            self._asr_q.qsize(),
        )

    def _on_chunk_closed(self, chunk) -> None:
        """Wrapper qui loggue la fermeture d'un chunk puis l'envoie au LLM."""
        logger.info(
            "[LIVE][CHUNKER] ✂ Chunk #%d fermé : %d turns, durée %.1fs, "
            "%d chars. Envoyé au LLM.",
            chunk.chunk_id, len(chunk.turns),
            chunk.end_time - chunk.start_time,
            len(chunk.text),
        )
        if self._llm_worker is not None:
            self._llm_worker.enqueue(chunk)

    def push(self, chunk: np.ndarray) -> None:
        """Appelé par AudioRecorder dans le callback audio. Non-bloquant."""
        if not self._running or self._error:
            return
        try:
            data = chunk.astype(np.float32, copy=True)
            self._asr_q.put_nowait(data)
            self._embed_q.put_nowait(data)
        except queue.Full:
            # Ne devrait pas arriver avec une queue non bornée, mais au cas où.
            pass

    def finalize(self, out_dir: Path) -> bool:
        """Stoppe les workers, aligne mots ↔ speakers, écrit transcript.txt
        (et compte_rendu.md si LLM live actif).

        Retourne True si le transcript a été écrit (mode live réussi).
        Retourne False si échec → le backend déclenche le fallback batch.
        """
        if not self._started:
            logger.warning("[LIVE][FINALIZE] LiveProcessor pas démarré (start() "
                           "n'a pas fini ou a échoué) — fallback batch")
            return False
        logger.info("[LIVE][FINALIZE] Arrêt des workers ASR/embed/turns…")
        self._running = False
        self._asr_q.put(None)
        self._embed_q.put(None)
        for t in self._threads:
            t.join(timeout=60.0)
        logger.info("[LIVE][FINALIZE] Workers arrêtés proprement")

        if self._error:
            logger.warning("[LIVE][FINALIZE] Erreur interne : %s — pas de "
                           "transcript écrit, fallback batch", self._error)
            return False

        # Si le LLM live est actif : ferme le dernier chunk + finalize worker
        # AVANT d'écrire le transcript, pour que compte_rendu.md soit dispo.
        out_dir = Path(out_dir)
        if self._llm_worker is not None:
            try:
                if self._turn_builder is not None and self._chunker is not None:
                    from .live_llm import split_turn_sentences
                    final_turns = self._turn_builder.finalize()
                    logger.info("[LIVE][FINALIZE] Drain final du TurnBuilder : "
                                "%d turns restantes", len(final_turns))
                    total_subs = 0
                    for turn in final_turns:
                        subs = split_turn_sentences(turn, max_chars=300)
                        for sub in subs:
                            self._chunker.add_turn(sub)
                        total_subs += len(subs)
                    logger.info("[LIVE][FINALIZE] Fermeture du chunker "
                                "(+%d phrases) — dernier chunk va être émis",
                                total_subs)
                    self._chunker.finalize()
                logger.info("[LIVE][FINALIZE] Attente fin queue LLM + "
                            "exec_summary + plan_attack…")
                self._llm_worker.out_dir = out_dir
                self._llm_worker.finalize()
            except Exception:
                logger.exception("[LIVE][FINALIZE] LLM finalize a levé")

        try:
            # 1. Clustering — finalize force le bootstrap si < 10 min.
            labels = self._clusterer.finalize() if self._clusterer else []
            if len(labels) != len(self._embedding_vecs):
                logger.warning("Désalignement labels/embeddings (%d vs %d) — on coupe",
                               len(labels), len(self._embedding_vecs))
                labels = labels[:len(self._embedding_vecs)]

            # 2. Align words to speakers.
            from diar_pipeline.transcription import (
                align_words_to_speakers, words_to_turns, format_transcript_txt,
            )
            from diar_pipeline.models import Segment

            # Construction de segments (fusion consecutive same-speaker).
            segments = self._build_segments(labels)
            if not segments:
                logger.warning("Aucun segment speaker — probable qu'aucune parole "
                               "n'a été détectée")
                return False

            words_mid = align_words_to_speakers([dict(w) for w in self._asr_words],
                                                 segments)
            turns_mid = words_to_turns(words_mid)

            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            transcript_path = out_dir / "transcript.txt"
            transcript_path.write_text(
                format_transcript_txt(turns_mid, with_timestamps=True),
                encoding="utf-8",
            )

            # Fichiers debug JSON — utiles si l'utilisateur veut inspecter
            # mais non critiques (seront supprimés au cleanup).
            import json
            (out_dir / "words.json").write_text(
                json.dumps(words_mid, ensure_ascii=False, indent=2), encoding="utf-8")
            (out_dir / "turns.json").write_text(
                json.dumps(turns_mid, ensure_ascii=False, indent=2), encoding="utf-8")

            logger.info(
                "[LIVE][FINALIZE] ✓ transcript.txt écrit : %d mots, %d turns, "
                "%d locuteurs",
                len(words_mid), len(turns_mid), self._clusterer.n_speakers,
            )
            return True
        except Exception as exc:
            self._error = f"Finalize: {exc}"
            logger.exception("[LIVE][FINALIZE] ÉCHEC d'écriture transcript")
            return False

    # ── Workers ────────────────────────────────────────────────────────────
    def _asr_worker(self) -> None:
        """Streaming ASR via sherpa-onnx. Polling des mots toutes les ~2s
        pour les émettre vers le TurnBuilder en temps réel si le LLM live
        est actif. Mots finaux stockés dans self._asr_words à la fin."""
        try:
            import sherpa_onnx
            from diar_pipeline.transcription import DEFAULT_MODEL_DIR, _tokens_to_words
            md = DEFAULT_MODEL_DIR
            rec = sherpa_onnx.OnlineRecognizer.from_transducer(
                encoder=str(md / "encoder.onnx"),
                decoder=str(md / "decoder.onnx"),
                joiner=str(md / "joiner.onnx"),
                tokens=str(md / "tokens.txt"),
                num_threads=2,  # laisse du CPU aux autres workers
                sample_rate=SAMPLE_RATE,
                feature_dim=80,
                decoding_method="greedy_search",
                enable_endpoint_detection=False,
            )
            stream = rec.create_stream()
            live_llm = self._llm_worker is not None
            logger.info("[LIVE][ASR] Worker démarré, consommation de la file "
                        "(taille courante : %d chunks)", self._asr_q.qsize())

            prev_words_count = 0
            last_poll = time.time()
            last_status_log = time.time()
            POLL_INTERVAL = 2.0
            STATUS_INTERVAL = 30.0  # log d'état toutes les 30s

            while True:
                chunk = self._asr_q.get()
                if chunk is None:
                    break
                stream.accept_waveform(SAMPLE_RATE, chunk)
                while rec.is_ready(stream):
                    rec.decode_stream(stream)
                # Poll périodique des mots nouvellement décodés.
                if time.time() - last_poll >= POLL_INTERVAL:
                    last_poll = time.time()
                    tokens = rec.tokens(stream)
                    timestamps = rec.timestamps(stream)
                    words = _tokens_to_words(tokens, timestamps)
                    if len(words) > prev_words_count:
                        new_words = words[prev_words_count:]
                        with self._asr_words_lock:
                            self._asr_words = words
                        prev_words_count = len(words)
                        if live_llm:
                            self._feed_words_to_turns(new_words)
                # Log d'état périodique.
                if time.time() - last_status_log >= STATUS_INTERVAL:
                    last_status_log = time.time()
                    logger.info(
                        "[LIVE][ASR] %d mots décodés, file audio = %d chunks "
                        "en attente", prev_words_count, self._asr_q.qsize())

            # Flush final : un peu de silence pour sortir le dernier token.
            tail = np.zeros(int(0.5 * SAMPLE_RATE), dtype=np.float32)
            stream.accept_waveform(SAMPLE_RATE, tail)
            while rec.is_ready(stream):
                rec.decode_stream(stream)

            tokens = rec.tokens(stream)
            timestamps = rec.timestamps(stream)
            final_words = _tokens_to_words(tokens, timestamps)
            with self._asr_words_lock:
                self._asr_words = final_words
            # Émet le reliquat au TurnBuilder.
            if live_llm and len(final_words) > prev_words_count:
                self._feed_words_to_turns(final_words[prev_words_count:])
            logger.info("ASR worker : %d mots", len(final_words))
        except Exception as exc:
            self._error = f"ASR: {exc}"
            logger.exception("ASR worker a planté")

    def _feed_words_to_turns(self, words: list[dict]) -> None:
        """Alimente le TurnBuilder avec les mots annotés du meilleur speaker
        disponible (nearest-in-time embedding → label). Sans clustering
        bootstrappé, on utilise 'SPEAKER_?' comme placeholder."""
        if self._turn_builder is None:
            return
        for w in words:
            w_copy = dict(w)
            w_copy["speaker"] = self._speaker_at_time(
                (w["start"] + w["end"]) / 2.0
            )
            self._turn_builder.add_word(w_copy)

    def _speaker_at_time(self, t: float) -> str:
        """Cherche l'embedding le plus proche en temps dans le clusterer.
        Retourne 'SPEAKER_?' pendant la phase de bootstrap (le clusterer
        n'a pas encore de labels)."""
        if self._clusterer is None or not self._clusterer.bootstrapped:
            return "SPEAKER_?"
        # Recherche linéaire inverse (les derniers ajouts sont proches de t).
        times = self._embedding_times
        labels = self._clusterer._labels if hasattr(self._clusterer, "_labels") else []
        if not times or not labels:
            return "SPEAKER_?"
        # Recherche dichotomique grossière.
        n = min(len(times), len(labels))
        # Parcours à rebours ; en captation live c'est très rapide en pratique.
        best_i, best_d = 0, abs(times[0] - t)
        for i in range(1, n):
            d = abs(times[i] - t)
            if d < best_d:
                best_i, best_d = i, d
        return f"SPEAKER_{labels[best_i]:02d}"

    def _turn_dispatch_worker(self) -> None:
        """Périodiquement : drain TurnBuilder → découpage phrase par
        phrase (comme normalize_transcript batch) → chunker.add_turn()."""
        try:
            from .live_llm import split_turn_sentences
            logger.info("[LIVE][TURNS] Worker démarré, split phrases + "
                        "dispatch vers chunker")
            total_turns_sent = 0
            last_status_log = time.time()
            STATUS_INTERVAL = 45.0
            while self._running or (self._turn_builder and
                                     self._turn_builder._pending_turns):
                time.sleep(1.0)
                if self._turn_builder is None or self._chunker is None:
                    continue
                turns = self._turn_builder.drain()
                for turn in turns:
                    subs = split_turn_sentences(turn, max_chars=300)
                    for sub in subs:
                        self._chunker.add_turn(sub)
                    total_turns_sent += len(subs)
                if time.time() - last_status_log >= STATUS_INTERVAL:
                    last_status_log = time.time()
                    logger.info(
                        "[LIVE][TURNS] %d phrases envoyées au chunker",
                        total_turns_sent)
            logger.info("[LIVE][TURNS] Worker terminé : %d phrases envoyées "
                        "au chunker au total", total_turns_sent)
        except Exception as exc:
            logger.exception("[LIVE][TURNS] Worker a levé : %s", exc)

    def _embed_worker(self) -> None:
        """VAD sur chunks glissants, embedding toutes les 0.6s sur fenêtres 1.2s
        de parole, puis .add() au clusterer. Modèles préchargés dans start()."""
        try:
            logger.info("[LIVE][EMBED] Worker démarré, consommation de la file "
                        "(taille courante : %d chunks)", self._embed_q.qsize())
            buffer = np.zeros(0, dtype=np.float32)
            total_samples = 0
            last_status_log = time.time()
            STATUS_INTERVAL = 30.0
            last_bootstrap_state = False

            while True:
                chunk = self._embed_q.get()
                if chunk is None:
                    break
                buffer = np.concatenate([buffer, chunk])
                total_samples += len(chunk)

                while len(buffer) >= EMBED_WIN_SAMPLES:
                    window = buffer[:EMBED_WIN_SAMPLES]
                    if self._window_has_speech(window):
                        emb = self._extractor.extract_from_array(window, SAMPLE_RATE)
                        if emb is not None:
                            if emb.ndim == 2:
                                emb = emb[0]
                            t_start = (total_samples - len(buffer)) / SAMPLE_RATE
                            t_center = t_start + EMBED_WIN_S / 2
                            self._embedding_times.append(t_center)
                            self._embedding_vecs.append(emb)
                            self._clusterer.add(emb)
                            # Log quand le bootstrap diarisation se déclenche.
                            if (not last_bootstrap_state
                                    and self._clusterer.bootstrapped):
                                last_bootstrap_state = True
                                logger.info(
                                    "[LIVE][DIAR] 🎯 Bootstrap diarisation "
                                    "déclenché ! NMESC sur %d embeddings → "
                                    "%d locuteurs détectés, seuil online "
                                    "calibré à %.3f. Les prochains mots "
                                    "auront de vrais labels SPEAKER_XX.",
                                    len(self._embedding_vecs),
                                    self._clusterer.n_speakers,
                                    self._clusterer.auto_threshold,
                                )
                    buffer = buffer[EMBED_HOP_SAMPLES:]

                # Log d'état périodique.
                if time.time() - last_status_log >= STATUS_INTERVAL:
                    last_status_log = time.time()
                    n_emb = len(self._embedding_vecs)
                    n_spk = self._clusterer.n_speakers if self._clusterer else 0
                    state = "bootstrappé" if (self._clusterer
                                               and self._clusterer.bootstrapped
                                               ) else f"en bootstrap ({n_emb}/{BOOTSTRAP_SIZE})"
                    logger.info(
                        "[LIVE][EMBED] %d embeddings extraits, clusterer %s, "
                        "%d locuteurs, file = %d chunks",
                        n_emb, state, n_spk, self._embed_q.qsize())

            logger.info("[LIVE][EMBED] Worker terminé : %d embeddings, "
                        "%d locuteurs finaux",
                        len(self._embedding_vecs),
                        self._clusterer.n_speakers if self._clusterer else 0)
        except Exception as exc:
            self._error = f"Embed: {exc}"
            logger.exception("[LIVE][EMBED] Worker a planté")

    # ── Helpers ────────────────────────────────────────────────────────────
    def _window_has_speech(self, window: np.ndarray) -> bool:
        """Vrai si la fenêtre contient de la parole d'après silero VAD
        (préchargé dans start()). Fallback énergie RMS si modèle absent."""
        if self._vad_model is None:
            rms = float(np.sqrt(np.mean(window ** 2)))
            return rms > 0.01  # seuil grossier
        try:
            import torch
            t = torch.from_numpy(window.astype(np.float32))
            # On découpe la fenêtre en blocs de 512 et on regarde si AU MOINS
            # un bloc est de la parole.
            for i in range(0, len(t) - VAD_CHUNK_SAMPLES + 1, VAD_CHUNK_SAMPLES):
                prob = self._vad_model(t[i:i + VAD_CHUNK_SAMPLES],
                                        SAMPLE_RATE).item()
                if prob >= 0.4:
                    return True
            return False
        except Exception:
            # En cas de pépin, on laisse passer (mieux que perdre du signal).
            return True

    def _build_segments(self, labels: list[int]) -> list:
        """Fusionne les embeddings consécutifs du même locuteur en segments."""
        from diar_pipeline.models import Segment
        if not labels or not self._embedding_times:
            return []
        segs: list[Segment] = []
        cur_lab = labels[0]
        cur_start = self._embedding_times[0] - EMBED_WIN_S / 2
        cur_end = self._embedding_times[0] + EMBED_WIN_S / 2
        for i in range(1, len(labels)):
            t_c = self._embedding_times[i]
            t_s = t_c - EMBED_WIN_S / 2
            t_e = t_c + EMBED_WIN_S / 2
            if labels[i] == cur_lab and t_s <= cur_end + 0.1:
                cur_end = t_e
            else:
                segs.append(Segment(
                    start=cur_start, end=cur_end, speaker=f"SPEAKER_{cur_lab:02d}",
                ))
                cur_lab = labels[i]
                cur_start = t_s
                cur_end = t_e
        segs.append(Segment(
            start=cur_start, end=cur_end, speaker=f"SPEAKER_{cur_lab:02d}",
        ))
        return segs
