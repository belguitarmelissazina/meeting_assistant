"""
Logger CSV de l'usage RAM pendant que le backend tourne.

Écrit une ligne toutes les INTERVAL_S secondes avec :
  timestamp ISO, python_rss_mb, python_vms_mb,
  llama_rss_mb, llama_pids,
  system_used_mb, system_available_mb, system_percent,
  swap_used_mb, swap_percent

Le fichier CSV est créé au démarrage dans ~/.meeting_assistant/logs/
avec un nom horodaté. Parfait pour tracer une courbe dans Excel ou
pandas après coup.

Démarrage/arrêt via start()/stop(), pensé pour être appelés depuis les
hooks startup/shutdown de FastAPI.
"""
from __future__ import annotations

import csv
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

INTERVAL_S = 30.0
LOG_DIR = Path.home() / ".meeting_assistant" / "logs"

_HEADERS = [
    "timestamp",
    "uptime_s",
    "python_rss_mb",
    "python_vms_mb",
    "llama_rss_mb",
    "llama_pids",
    "system_used_mb",
    "system_available_mb",
    "system_percent",
    "swap_used_mb",
    "swap_percent",
]


class ResourceMonitor:
    def __init__(self, interval_s: float = INTERVAL_S) -> None:
        self.interval_s = interval_s
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._path: Path | None = None
        self._started_at: float | None = None

    @property
    def path(self) -> Path | None:
        return self._path

    def start(self) -> None:
        if self._thread is not None:
            return
        try:
            import psutil  # noqa: F401
        except ImportError:
            logger.warning("[RES] psutil indisponible — monitoring RAM désactivé")
            return

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%Hh%Mm%Ss")
        self._path = LOG_DIR / f"resource_{stamp}.csv"
        self._started_at = time.time()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="resource-monitor",
        )
        self._thread.start()
        logger.info("[RES] Monitoring RAM démarré → %s (interval %.0fs)",
                    self._path, self.interval_s)

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        logger.info("[RES] Monitoring RAM arrêté — fichier final : %s",
                    self._path)

    def _loop(self) -> None:
        import psutil
        try:
            with self._path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(_HEADERS)
                # Écrit immédiatement une première ligne (t=0).
                self._write_sample(writer, psutil)
                f.flush()
                while not self._stop_event.wait(self.interval_s):
                    self._write_sample(writer, psutil)
                    f.flush()
        except Exception:
            logger.exception("[RES] Le loop monitoring a planté")

    def _write_sample(self, writer, psutil) -> None:
        now_ts = datetime.now().isoformat(timespec="seconds")
        uptime = time.time() - (self._started_at or time.time())

        proc = psutil.Process(os.getpid())
        try:
            mem = proc.memory_info()
            py_rss_mb = mem.rss / (1024 * 1024)
            py_vms_mb = mem.vms / (1024 * 1024)
        except psutil.Error:
            py_rss_mb = 0.0
            py_vms_mb = 0.0

        llama_rss_mb = 0.0
        llama_pids: list[int] = []
        for p in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                name = (p.info.get("name") or "").lower()
                cmdline = " ".join(p.info.get("cmdline") or []).lower()
                if "llama-server" in name or "llama-server" in cmdline:
                    llama_rss_mb += p.memory_info().rss / (1024 * 1024)
                    llama_pids.append(p.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()

        writer.writerow([
            now_ts,
            round(uptime, 1),
            round(py_rss_mb, 1),
            round(py_vms_mb, 1),
            round(llama_rss_mb, 1),
            ",".join(str(p) for p in llama_pids) if llama_pids else "",
            round(vm.used / (1024 * 1024), 1),
            round(vm.available / (1024 * 1024), 1),
            round(vm.percent, 1),
            round(sw.used / (1024 * 1024), 1),
            round(sw.percent, 1),
        ])


_singleton: ResourceMonitor | None = None


def get_monitor() -> ResourceMonitor:
    global _singleton
    if _singleton is None:
        _singleton = ResourceMonitor()
    return _singleton
