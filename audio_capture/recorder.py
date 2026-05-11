"""
Enregistrement audio depuis le microphone et la sortie haut-parleur (loopback WASAPI).

Capture simultanée du micro et du son système, mélange les flux en mono 16kHz
et sauvegarde en fichier WAV prêt pour la transcription.
"""

import logging
import tempfile
import threading
import time
import wave

import numpy as np

logger = logging.getLogger(__name__)


class AudioRecorder:
    """
    Enregistre simultanément le microphone et la sortie système (loopback WASAPI).

    - Micro     : capturé via sounddevice
    - Loopback  : capturé via pyaudiowpatch (haut-parleur par défaut Windows)
    - Fallback  : soundcard, puis Stereo Mix si pyaudiowpatch échoue
    - Les deux flux sont mélangés en mono 16kHz et sauvegardés en WAV.
    """

    SAMPLE_RATE = 16_000
    BLOCK_SIZE  = 1_024

    def __init__(self, on_chunk=None) -> None:
        """
        on_chunk : callable(np.ndarray) optionnel. Appelé dans le callback
            audio avec chaque chunk MICRO (mono float32 16 kHz) dès qu'il
            arrive — utilisé par LiveProcessor pour router l'audio vers
            l'ASR/embedding en temps réel. Doit être NON-BLOQUANT.
        """
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._loopback_frames: list[np.ndarray] = []
        self._loopback_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._start_time: float | None = None
        self._level: float = 0.0
        self._loopback_level: float = 0.0
        self._has_loopback: bool = False
        self._error: str | None = None
        self._mic_first_chunk_time: float | None = None
        self._lb_first_chunk_time: float | None = None
        self._on_chunk = on_chunk

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def duration(self) -> float:
        if self._start_time and self._recording:
            return time.time() - self._start_time
        return 0.0

    @property
    def audio_level(self) -> float:
        return min(self._level, 1.0)

    @property
    def loopback_level(self) -> float:
        """RMS level of the loopback (speakers) audio stream."""
        return min(self._loopback_level, 1.0)

    @property
    def has_loopback(self) -> bool:
        """Whether a loopback device was detected and is active."""
        return self._has_loopback

    @property
    def loopback_sample_count(self) -> int:
        """Total number of loopback samples captured so far."""
        with self._loopback_lock:
            return sum(len(f) for f in self._loopback_frames)

    def get_loopback_buffer_since(self, sample_offset: int) -> "np.ndarray | None":
        """Return loopback (speakers) audio captured since `sample_offset`."""
        with self._loopback_lock:
            if not self._loopback_frames:
                return None
            buf = np.concatenate(self._loopback_frames)
        if sample_offset >= len(buf):
            return None
        return buf[sample_offset:]

    @property
    def sample_count(self) -> int:
        """Total number of samples captured so far."""
        with self._lock:
            return sum(len(f) for f in self._frames)

    def get_current_buffer(self) -> "np.ndarray | None":
        """Return a copy of all captured audio without stopping the recording."""
        with self._lock:
            if not self._frames:
                return None
            return np.concatenate(self._frames).copy()

    def get_buffer_since(self, sample_offset: int) -> "np.ndarray | None":
        """Return audio captured since `sample_offset` (in samples)."""
        buf = self.get_current_buffer()
        if buf is None or sample_offset >= len(buf):
            return None
        return buf[sample_offset:]

    def save_buffer_to_wav(self, audio: "np.ndarray") -> str:
        """Save an audio numpy array to a temporary WAV file. Returns the path."""
        return self._save_wav([audio])

    def start(self) -> None:
        if self._recording:
            return
        self._frames = []
        with self._loopback_lock:
            self._loopback_frames = []
        self._level = 0.0
        self._loopback_level = 0.0
        self._has_loopback = False
        self._error = None
        self._mic_first_chunk_time = None
        self._lb_first_chunk_time = None
        self._recording = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        logger.info("Enregistrement démarré")

    def stop(self) -> str | None:
        if not self._recording:
            return None
        self._recording = False
        if self._thread:
            self._thread.join(timeout=10.0)
            self._thread = None
        with self._lock:
            frames = list(self._frames)
        if not frames:
            logger.warning("Aucune donnée audio capturée")
            return None
        return self._save_wav(frames)

    # ------------------------------------------------------------------
    # Boucle d'enregistrement
    # ------------------------------------------------------------------

    def _record_loop(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice non installé")
            self._recording = False
            return

        mic_buffer: list[np.ndarray] = []
        loopback_buffer: list[np.ndarray] = []
        mic_lock = threading.Lock()
        loopback_lock = threading.Lock()

        def mic_callback(indata, frames, time_info, status):
            if self._recording:
                if self._mic_first_chunk_time is None:
                    self._mic_first_chunk_time = time.time()
                chunk = indata[:, 0].copy()
                with mic_lock:
                    mic_buffer.append(chunk)
                # Also accumulate in self._frames for live buffer access
                with self._lock:
                    self._frames.append(chunk.copy())
                # NB: on_chunk est appelé par _live_mix_worker et non ici,
                # pour pouvoir mixer mic+loopback avant forward.
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                self._level = min(rms * 8, 1.0)

        # Démarrage loopback
        loopback_thread: threading.Thread | None = None
        loopback_info = self._find_loopback_device()

        if loopback_info is not None:
            method, device_id = loopback_info
            loopback_thread = threading.Thread(
                target=self._loopback_worker,
                args=(method, device_id, loopback_buffer, loopback_lock),
                daemon=True,
            )
            loopback_thread.start()
            self._has_loopback = True
            logger.info("Capture loopback activée via %s", method)
        else:
            logger.info("Loopback non disponible — microphone seul")

        # Live mix worker — mixe mic+loopback en streaming et forward vers
        # on_chunk. Si pas de loopback, forward le mic tel quel.
        mix_thread: threading.Thread | None = None
        if self._on_chunk is not None:
            mix_thread = threading.Thread(
                target=self._live_mix_worker,
                args=(mic_buffer, mic_lock, loopback_buffer, loopback_lock,
                      loopback_info is not None),
                daemon=True,
                name="live-mix",
            )
            mix_thread.start()

        # Flux microphone — WASAPI shared mode pour coexister avec Teams/Zoom
        mic_extra = {}
        try:
            import sounddevice as sd
            wasapi_id = None
            for api in sd.query_hostapis():
                if "WASAPI" in api["name"]:
                    wasapi_id = api["index"]
                    break
            if wasapi_id is not None:
                default_in = sd.query_hostapis(wasapi_id).get("default_input_device", -1)
                if default_in >= 0:
                    mic_extra["device"] = default_in
                    mic_extra["extra_settings"] = sd.WasapiSettings(exclusive=False)
                    logger.info("Micro ouvert en WASAPI shared mode (device=%d)", default_in)
        except Exception as exc:
            logger.debug("WASAPI shared mode non disponible, fallback défaut : %s", exc)

        max_reconnects = 5
        reconnect_delay = 2.0
        for attempt in range(max_reconnects + 1):
            try:
                with sd.InputStream(
                    samplerate=self.SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                    callback=mic_callback,
                    blocksize=self.BLOCK_SIZE,
                    **mic_extra,
                ):
                    if attempt > 0:
                        logger.info("Micro reconnecté (tentative %d)", attempt)
                        self._error = None
                    while self._recording:
                        time.sleep(0.05)
                break  # Arrêt normal demandé par stop()
            except Exception as exc:
                if not self._recording:
                    break  # Arrêt demandé, pas une erreur
                logger.error("Erreur flux microphone (tentative %d/%d) : %s",
                             attempt + 1, max_reconnects + 1, exc)
                self._error = str(exc)
                if attempt < max_reconnects:
                    logger.info("Reconnexion micro dans %.0fs...", reconnect_delay)
                    # Attente interruptible
                    for _ in range(int(reconnect_delay * 10)):
                        if not self._recording:
                            break
                        time.sleep(0.1)
                    reconnect_delay = min(reconnect_delay * 1.5, 10.0)

        self._recording = False

        if loopback_thread:
            loopback_thread.join(timeout=5.0)
        if mix_thread:
            mix_thread.join(timeout=5.0)

        # Assemblage
        with mic_lock:
            mic_data = np.concatenate(mic_buffer) if mic_buffer else np.array([], dtype=np.float32)
        with loopback_lock:
            lb_data = np.concatenate(loopback_buffer) if loopback_buffer else np.array([], dtype=np.float32)

        if len(mic_data) == 0:
            return

        if len(lb_data) > 0:
            # Align streams by wall-clock first-chunk timestamps.
            # Without this, mic_data[0] and lb_data[0] correspond to different real times
            # (loopback usually starts first), causing voices to be shifted and overlap.
            offset_samples = 0
            if self._mic_first_chunk_time is not None and self._lb_first_chunk_time is not None:
                delta = self._lb_first_chunk_time - self._mic_first_chunk_time
                offset_samples = int(round(delta * self.SAMPLE_RATE))
            if offset_samples > 0:
                lb_data = np.concatenate([np.zeros(offset_samples, dtype=np.float32), lb_data])
            elif offset_samples < 0:
                mic_data = np.concatenate([np.zeros(-offset_samples, dtype=np.float32), mic_data])
            max_len = max(len(mic_data), len(lb_data))
            if len(mic_data) < max_len:
                mic_data = np.concatenate([mic_data, np.zeros(max_len - len(mic_data), dtype=np.float32)])
            if len(lb_data) < max_len:
                lb_data = np.concatenate([lb_data, np.zeros(max_len - len(lb_data), dtype=np.float32)])
            mixed = self._mix_with_ducking(mic_data, lb_data)
            logger.info("Micro + loopback mélangés avec ducking (%d échantillons, offset=%+d)", max_len, offset_samples)
        else:
            mixed = mic_data
            logger.info("Micro seul (%d échantillons)", len(mic_data))

        with self._lock:
            self._frames = [mixed]

    # ------------------------------------------------------------------
    # Détection du périphérique loopback
    # ------------------------------------------------------------------

    def _find_loopback_device(self):
        """
        Cherche le loopback du haut-parleur par défaut Windows.

        Ordre :
          1. pyaudiowpatch (WASAPI loopback — haut-parleur par défaut)
          2. soundcard     (fallback)
          3. Stereo Mix    (sounddevice, si activé dans Windows)
        """
        # 1. pyaudiowpatch
        try:
            import pyaudiowpatch as pyaudio
            p = pyaudio.PyAudio()
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)

                default_out_name = ""
                try:
                    default_out_name = p.get_default_output_device_info()["name"].lower()
                except Exception:
                    pass

                loopbacks = []
                for i in range(p.get_device_count()):
                    dev = p.get_device_info_by_index(i)
                    if dev["hostApi"] == wasapi_info["index"] and dev.get("isLoopbackDevice", False):
                        loopbacks.append((i, dev["name"]))

                if loopbacks:
                    if default_out_name:
                        for idx, name in loopbacks:
                            clean = name.replace(" [Loopback]", "").strip().lower()
                            if clean in default_out_name or default_out_name in clean:
                                logger.info("Loopback pyaudiowpatch (défaut) : [%d] %s", idx, name)
                                return ("pyaudiowpatch", idx)
                    idx, name = loopbacks[0]
                    logger.info("Loopback pyaudiowpatch (premier) : [%d] %s", idx, name)
                    return ("pyaudiowpatch", idx)
            finally:
                p.terminate()
        except ImportError:
            logger.debug("pyaudiowpatch non installé")
        except Exception as exc:
            logger.debug("pyaudiowpatch échec : %s", exc)

        # 2. soundcard
        try:
            import soundcard as sc
            spk = sc.default_speaker()
            lb = sc.get_microphone(spk.id, include_loopback=True)
            logger.info("Loopback soundcard : %s", lb.name)
            return ("soundcard", lb)
        except ImportError:
            logger.debug("soundcard non installé")
        except Exception as exc:
            logger.debug("soundcard échec : %s", exc)

        # 3. Stereo Mix
        try:
            import sounddevice as sd
            for i, dev in enumerate(sd.query_devices()):
                name = dev["name"].lower()
                if any(kw in name for kw in ("stereo mix", "mixage stéréo", "mixage stereo", "what u hear")):
                    if dev["max_input_channels"] > 0:
                        logger.info("Stereo Mix trouvé : [%d] %s", i, dev["name"])
                        return ("sounddevice_stereomix", i)
        except Exception as exc:
            logger.debug("Stereo Mix : %s", exc)

        return None

    # ------------------------------------------------------------------
    # Workers loopback
    # ------------------------------------------------------------------

    def _loopback_worker(self, method: str, device_id, loopback_buffer: list, lock: threading.Lock) -> None:
        if method == "pyaudiowpatch":
            self._loopback_pyaudiowpatch(device_id, loopback_buffer, lock)
        elif method == "soundcard":
            self._loopback_soundcard(device_id, loopback_buffer, lock)
        elif method == "sounddevice_stereomix":
            self._loopback_sounddevice(device_id, loopback_buffer, lock)

    def _loopback_pyaudiowpatch(self, device_index: int, loopback_buffer: list, lock: threading.Lock) -> None:
        try:
            import pyaudiowpatch as pyaudio
            p = pyaudio.PyAudio()
            dev_info = p.get_device_info_by_index(device_index)
            sr = int(dev_info["defaultSampleRate"])
            channels = int(dev_info["maxInputChannels"]) or 2
            chunk = int(sr * 0.05)

            stream = None
            actual_ch = channels
            for ch_try in ((channels, 1) if channels != 1 else (1,)):
                try:
                    stream = p.open(
                        format=pyaudio.paFloat32,
                        channels=ch_try,
                        rate=sr,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=chunk,
                    )
                    actual_ch = ch_try
                    break
                except Exception:
                    pass

            if stream is None:
                logger.warning("Loopback pyaudiowpatch inaccessible — microphone seul")
                p.terminate()
                return

            logger.info("Loopback stream ouvert (sr=%d ch=%d)", sr, actual_ch)
            self._has_loopback = True
            first_chunk_logged = False

            while self._recording:
                try:
                    if stream.get_read_available() >= chunk:
                        raw = stream.read(chunk, exception_on_overflow=False)
                        if self._lb_first_chunk_time is None:
                            self._lb_first_chunk_time = time.time()
                        audio = np.frombuffer(raw, dtype=np.float32)
                        if actual_ch > 1:
                            audio = audio.reshape(-1, actual_ch).mean(axis=1)
                        if sr != self.SAMPLE_RATE:
                            new_len = int(len(audio) * self.SAMPLE_RATE / sr)
                            audio = np.interp(
                                np.linspace(0, len(audio) - 1, new_len),
                                np.arange(len(audio)),
                                audio,
                            ).astype(np.float32)
                        rms = float(np.sqrt(np.mean(audio ** 2)))
                        self._loopback_level = min(rms * 8, 1.0)
                        if not first_chunk_logged:
                            logger.info("Loopback premier chunk reçu — RMS=%.4f level=%.4f", rms, self._loopback_level)
                            first_chunk_logged = True
                        with self._loopback_lock:
                            self._loopback_frames.append(audio.copy())
                        with lock:
                            loopback_buffer.append(audio)
                    else:
                        time.sleep(0.01)
                except Exception:
                    time.sleep(0.01)

            stream.stop_stream()
            stream.close()
            p.terminate()
            logger.info("Loopback arrêté (%d chunks)", len(loopback_buffer))

        except Exception as exc:
            logger.warning("Loopback non disponible (%s) — microphone seul", exc)

    def _loopback_soundcard(self, loopback_device, loopback_buffer: list, lock: threading.Lock) -> None:
        try:
            self._has_loopback = True
            chunk_frames = int(self.SAMPLE_RATE * 0.05)
            with loopback_device.recorder(samplerate=self.SAMPLE_RATE, channels=1) as rec:
                while self._recording:
                    chunk = rec.record(numframes=chunk_frames)[:, 0].astype(np.float32)
                    if self._lb_first_chunk_time is None:
                        self._lb_first_chunk_time = time.time()
                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                    self._loopback_level = min(rms * 8, 1.0)
                    with self._loopback_lock:
                        self._loopback_frames.append(chunk.copy())
                    with lock:
                        loopback_buffer.append(chunk)
        except Exception as exc:
            logger.debug("soundcard worker arrêté : %s", exc)

    def _loopback_sounddevice(self, device_index: int, loopback_buffer: list, lock: threading.Lock) -> None:
        try:
            self._has_loopback = True
            import sounddevice as sd
            buf: list[np.ndarray] = []
            buf_lock = threading.Lock()

            def cb(indata, frames, t, status):
                if self._lb_first_chunk_time is None:
                    self._lb_first_chunk_time = time.time()
                with buf_lock:
                    buf.append(indata[:, 0].copy())

            with sd.InputStream(device=device_index, samplerate=self.SAMPLE_RATE,
                                channels=1, dtype="float32", callback=cb,
                                blocksize=self.BLOCK_SIZE):
                while self._recording:
                    time.sleep(0.05)
                    with buf_lock:
                        if buf:
                            chunk = np.concatenate(buf)
                            buf.clear()
                            rms = float(np.sqrt(np.mean(chunk ** 2)))
                            self._loopback_level = min(rms * 8, 1.0)
                            with self._loopback_lock:
                                self._loopback_frames.append(chunk.copy())
                            with lock:
                                loopback_buffer.append(chunk)
        except Exception as exc:
            logger.debug("Stereo Mix worker arrêté : %s", exc)

    # ------------------------------------------------------------------
    # Mixage avec ducking (anti-echo)
    # ------------------------------------------------------------------

    def _mix_with_ducking(
        self,
        mic: np.ndarray,
        lb: np.ndarray,
        window_ms: int = 120,
        lb_active_rms: float = 0.015,
    ) -> np.ndarray:
        """Mix mic + loopback while cancelling the acoustic leak.

        Problem: if the user is on laptop speakers (not headphones), the mic
        physically picks up the remote participant's voice. Loopback captures
        the same voice digitally. A naive sum produces a doubled voice.

        Strategy per window:
          - loopback silent  → keep mic (user voice)
          - loopback active + mic weaker → mic is mostly leak, suppress it
          - loopback active + mic much louder → user is talking over remote,
            keep both
        """
        n = min(len(mic), len(lb))
        if n == 0:
            return np.array([], dtype=np.float32)

        win = max(1, int(self.SAMPLE_RATE * window_ms / 1000))
        out = np.empty(n, dtype=np.float32)
        prev_mic_gain = 0.8
        smoothing = 0.25  # per-window gain smoothing to avoid clicks

        lb_gain = 0.9
        mic_gain_normal = 0.8
        mic_gain_ducked = 0.08
        user_over_remote_ratio = 1.6

        for start in range(0, n, win):
            end = min(start + win, n)
            mic_win = mic[start:end]
            lb_win = lb[start:end]
            mic_rms = float(np.sqrt(np.mean(mic_win ** 2))) if mic_win.size else 0.0
            lb_rms = float(np.sqrt(np.mean(lb_win ** 2))) if lb_win.size else 0.0

            if lb_rms > lb_active_rms and mic_rms < lb_rms * user_over_remote_ratio:
                target_mic_gain = mic_gain_ducked
            else:
                target_mic_gain = mic_gain_normal

            mic_gain = prev_mic_gain + (target_mic_gain - prev_mic_gain) * smoothing
            prev_mic_gain = mic_gain

            out[start:end] = mic_win * mic_gain + lb_win * lb_gain

        return np.clip(out, -1.0, 1.0)

    # ------------------------------------------------------------------
    # Live mix worker — mixe mic+loopback en streaming pour la pipeline live
    # ------------------------------------------------------------------

    def _live_mix_worker(
        self,
        mic_buffer: list,
        mic_lock: threading.Lock,
        lb_buffer: list,
        lb_lock: threading.Lock,
        has_loopback: bool,
        poll_interval: float = 0.05,
        min_forward_samples: int = 512,
    ) -> None:
        """Consomme mic_buffer (+ lb_buffer si présent), mixe avec ducking
        cohérent inter-chunks, et forward vers self._on_chunk.

        Alignement mic/loopback : ajustement one-shot sur les wall-clock
        timestamps des premiers chunks de chaque stream, identique à la
        logique offline existante (lignes ~275-285).
        """
        mic_cursor = 0   # nb de chunks mic déjà consommés
        lb_cursor = 0
        mic_pending = np.zeros(0, dtype=np.float32)
        lb_pending = np.zeros(0, dtype=np.float32)
        aligned = not has_loopback  # rien à aligner si pas de loopback
        prev_mic_gain = 0.8  # continuité inter-chunks du ducking

        # Paramètres du ducking (identiques à _mix_with_ducking)
        lb_active_rms = 0.015
        mic_gain_normal = 0.8
        mic_gain_ducked = 0.08
        user_over_remote_ratio = 1.6
        lb_gain = 0.9
        smoothing = 0.25

        while True:
            time.sleep(poll_interval)

            # Récupère les nouveaux chunks mic.
            with mic_lock:
                new_mic = mic_buffer[mic_cursor:]
                mic_cursor = len(mic_buffer)
            if new_mic:
                mic_pending = np.concatenate([mic_pending, *new_mic])

            if has_loopback:
                with lb_lock:
                    new_lb = lb_buffer[lb_cursor:]
                    lb_cursor = len(lb_buffer)
                if new_lb:
                    lb_pending = np.concatenate([lb_pending, *new_lb])

                # Alignement wall-clock one-shot. On trim le stream qui a de
                # l'avance (symétrique du pad-zéros de la version offline), et
                # uniquement quand assez d'échantillons sont dispo pour couvrir
                # tout l'offset d'un coup — sinon on attend la prochaine
                # itération sans toucher aux pendings, pour éviter de stripper
                # les chunks au fur et à mesure qu'ils arrivent.
                if (not aligned
                        and self._mic_first_chunk_time is not None
                        and self._lb_first_chunk_time is not None):
                    delta = self._lb_first_chunk_time - self._mic_first_chunk_time
                    offset = int(round(delta * self.SAMPLE_RATE))
                    if offset > 0:
                        # lb a démarré après mic → mic a du surplus → trim mic
                        if len(mic_pending) >= offset:
                            mic_pending = mic_pending[offset:]
                            aligned = True
                    elif offset < 0:
                        # lb a démarré avant mic → lb a du surplus → trim lb
                        if len(lb_pending) >= -offset:
                            lb_pending = lb_pending[-offset:]
                            aligned = True
                    else:
                        aligned = True
                if not aligned:
                    # Attend encore que les deux timestamps soient dispos
                    # et/ou que le buffer en retard rattrape.
                    if (not self._recording
                            and not new_mic and not new_lb):
                        break
                    continue

                n = min(len(mic_pending), len(lb_pending))
                if n < min_forward_samples:
                    if not self._recording and not new_mic and not new_lb:
                        # Flush final : mixe ce qu'on a.
                        if n > 0:
                            pass  # traite plus bas
                        else:
                            break
                    else:
                        continue
                mic_chunk = mic_pending[:n]
                lb_chunk = lb_pending[:n]
                mic_pending = mic_pending[n:]
                lb_pending = lb_pending[n:]

                # Ducking avec gain continu inter-chunks.
                mic_rms = float(np.sqrt(np.mean(mic_chunk ** 2))) if n else 0.0
                lb_rms = float(np.sqrt(np.mean(lb_chunk ** 2))) if n else 0.0
                if lb_rms > lb_active_rms and mic_rms < lb_rms * user_over_remote_ratio:
                    target = mic_gain_ducked
                else:
                    target = mic_gain_normal
                mic_gain = prev_mic_gain + (target - prev_mic_gain) * smoothing
                prev_mic_gain = mic_gain
                mixed = np.clip(mic_chunk * mic_gain + lb_chunk * lb_gain, -1.0, 1.0)
            else:
                # Pas de loopback : forward le mic tel quel.
                if len(mic_pending) < min_forward_samples:
                    if not self._recording and not new_mic:
                        if len(mic_pending) > 0:
                            mixed = mic_pending
                            mic_pending = np.zeros(0, dtype=np.float32)
                        else:
                            break
                    else:
                        continue
                else:
                    mixed = mic_pending
                    mic_pending = np.zeros(0, dtype=np.float32)

            try:
                self._on_chunk(mixed.astype(np.float32, copy=False))
            except Exception:
                logger.exception("on_chunk a levé dans live_mix_worker")

    # ------------------------------------------------------------------
    # Sauvegarde WAV
    # ------------------------------------------------------------------

    def _save_wav(self, frames: list[np.ndarray]) -> str:
        audio = np.clip(np.concatenate(frames), -1.0, 1.0)
        audio_int16 = (audio * 32_767).astype(np.int16)
        tmp = tempfile.NamedTemporaryFile(
            suffix=".wav", prefix="enregistrement_", delete=False,
        )
        tmp.close()
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())
        logger.info("Audio sauvegardé : %s (%.1f s)", tmp.name, len(audio) / self.SAMPLE_RATE)
        return tmp.name
