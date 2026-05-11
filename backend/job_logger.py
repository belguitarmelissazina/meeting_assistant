"""Logger par job : capture tout ce qui se passe pendant un traitement
(captation live + finalize + pipeline batch) dans un fichier markdown
dédié au sein du dossier de la réunion.

Format du fichier produit (`traitement.md`) :

    # Traitement — <label>

    - Job ID, dates, durée totale
    - Tableau récap des étapes (nom + durée)
    - Référence vers le CSV RAM
    - Logs détaillés horodatés (fenced code block)

Usage :

    logger = JobLogger(folder / "traitement.md", job.id, label="Réunion X")
    logger.start_step("Diarisation")
    ... du travail ...
    logger.end_step()
    logger.start_step("Compte rendu")
    ...
    logger.close()  # écrit le récap en tête + détache le FileHandler

Le FileHandler est attaché au root logger : tout ce que le backend logue
pendant la durée du job atterrit dans le fichier en plus de la console.
Pour relocaliser le fichier en cours de route (cas live : tmp dir →
dossier final au record_stop), utiliser `move(new_path)`.
"""
from __future__ import annotations

import logging
import shutil
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class JobLogger:
    def __init__(self, path: Path, job_id: str, label: str) -> None:
        self.path = Path(path)
        self.job_id = job_id
        self.label = label
        self._t_start = time.time()
        self._t_stop_clicked: float | None = None
        self._steps: list[dict] = []
        self._current_step: dict | None = None
        self._lock = threading.Lock()
        self._fh: logging.FileHandler | None = None
        self._closed = False
        self._init_file()
        self._attach()

    @property
    def closed(self) -> bool:
        return self._closed

    # ── Setup ───────────────────────────────────────────────────────────────
    def _init_file(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(
                f"# Traitement — {self.label}\n\n"
                f"- **Job ID** : `{self.job_id}`\n"
                f"- **Démarré** : "
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._t_start))}\n\n"
                "## Logs détaillés\n\n```\n",
                encoding="utf-8",
            )

    def _attach(self) -> None:
        fh = logging.FileHandler(self.path, mode="a", encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(_LOG_FORMAT))
        logging.getLogger().addHandler(fh)
        self._fh = fh

    def _detach(self) -> None:
        if self._fh is not None:
            logging.getLogger().removeHandler(self._fh)
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None

    # ── API publique ────────────────────────────────────────────────────────
    def move(self, new_path: Path) -> None:
        """Déplace le fichier vers `new_path` et ré-attache le FileHandler.
        Indispensable sur Windows : on ne peut pas mv/rename un fichier dont
        un FileHandler est ouvert. Si `new_path` existe déjà (ex. logger
        d'une session précédente avec le même nom), on l'écrase."""
        new_path = Path(new_path)
        if new_path == self.path:
            return
        self._detach()
        new_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if new_path.exists():
                new_path.unlink()
            if self.path.exists():
                shutil.move(str(self.path), str(new_path))
        except OSError as exc:
            logger.warning("[JOBLOG] Move %s → %s a échoué : %s",
                           self.path, new_path, exc)
        self.path = new_path
        self._attach()

    def mark_stop_clicked(self) -> None:
        """À appeler pile au moment où l'utilisateur clique 'Arrêter'.
        Utilisé pour mesurer la 'latence ressentie' = temps entre le clic
        Stop et la disponibilité du compte rendu (cf. summary)."""
        self._t_stop_clicked = time.time()
        logging.getLogger("backend").info(
            "⏱  STOP cliqué — chrono 'attente compte rendu' démarré")

    def start_step(self, name: str) -> None:
        """Démarre une étape (ferme la précédente si encore ouverte)."""
        with self._lock:
            if self._current_step is not None:
                self._end_step_locked()
            self._current_step = {"name": name, "t_start": time.time()}
        logging.getLogger("backend").info("▶ Étape : %s", name)

    def end_step(self) -> None:
        with self._lock:
            self._end_step_locked()

    def _end_step_locked(self) -> None:
        if self._current_step is None:
            return
        duration = time.time() - self._current_step["t_start"]
        self._current_step["duration_s"] = round(duration, 2)
        name = self._current_step["name"]
        self._steps.append(self._current_step)
        self._current_step = None
        logging.getLogger("backend").info(
            "✓ Étape '%s' terminée en %.1fs", name, duration)

    def append_raw(self, line: str) -> None:
        """Écrit une ligne brute dans le fichier (sans passer par logging).
        Utilisé pour la sortie stdout des subprocess (qui ont déjà leurs
        propres timestamps internes)."""
        if self._fh is None:
            return
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def close(self) -> None:
        """Ferme l'étape courante, détache le handler, et ré-écrit le
        fichier avec le tableau récap des étapes en tête."""
        if self._closed:
            return
        self.end_step()
        self._detach()
        self._closed = True
        try:
            self._rewrite_with_summary()
        except Exception:
            logger.exception("[JOBLOG] Écriture résumé a levé")

    def _rewrite_with_summary(self) -> None:
        try:
            content = self.path.read_text(encoding="utf-8")
        except OSError:
            content = ""
        # Préserve la section "## Logs détaillés" (créée à _init_file).
        idx = content.find("## Logs détaillés")
        logs_part = content[idx:] if idx >= 0 else "## Logs détaillés\n\n```\n"
        # S'assure que le fenced block est fermé.
        if logs_part.count("```") % 2 == 1:
            logs_part = logs_part.rstrip() + "\n```\n"

        total = time.time() - self._t_start
        out = []
        out.append(f"# Traitement — {self.label}\n\n")
        out.append(f"- **Job ID** : `{self.job_id}`\n")
        out.append(
            f"- **Démarré** : "
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._t_start))}\n"
        )
        out.append(
            f"- **Terminé** : "
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        out.append(f"- **Durée totale** : {total:.1f}s ({total/60:.1f} min)\n")
        if self._t_stop_clicked is not None:
            post_stop = time.time() - self._t_stop_clicked
            out.append(
                f"- **⏱ Attente post-clic STOP** : "
                f"**{post_stop:.1f}s** ({post_stop/60:.1f} min) "
                f"— temps entre la fin de réunion et la dispo du compte rendu\n"
            )
        out.append("\n## Résumé des étapes\n\n")
        if self._steps:
            out.append("| # | Étape | Durée |\n")
            out.append("|---|---|---|\n")
            for i, s in enumerate(self._steps, 1):
                out.append(f"| {i} | {s['name']} | {s['duration_s']:.1f}s |\n")
        else:
            out.append("_Aucune étape enregistrée._\n")
        out.append("\n## Monitoring RAM\n\n")
        out.append(
            "Échantillonné toutes les 30s par `backend/resource_monitor.py` "
            "→ `~/.meeting_assistant/logs/resource_*.csv` "
            "(ouvrable dans Excel ou pandas pour tracer la courbe).\n\n"
        )
        try:
            self.path.write_text("".join(out) + logs_part, encoding="utf-8")
        except OSError as exc:
            logger.warning("[JOBLOG] Réécriture finale a échoué : %s", exc)


# ── Singleton actif ────────────────────────────────────────────────────────
# Un seul JobLogger actif à la fois (le pipeline batch est sérialisé via
# pipeline_lock, et un seul enregistrement live à la fois). Ça évite
# d'avoir plusieurs FileHandlers attachés au root logger qui se marchent
# dessus.
_active: JobLogger | None = None
_active_lock = threading.Lock()


def get_active() -> JobLogger | None:
    return _active


def set_active(logger_obj: JobLogger | None) -> None:
    """Remplace l'actif. Si l'ancien existe et n'est pas fermé, on le ferme
    proprement avant de le remplacer (perte du log en cours = mieux que
    deux handlers concurrents sur le root logger)."""
    global _active
    with _active_lock:
        if _active is not None and not _active.closed:
            try:
                _active.close()
            except Exception:
                pass
        _active = logger_obj
