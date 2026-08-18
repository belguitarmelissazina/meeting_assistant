"""Worker de l'advisor live (Mistral) — recommandations temps réel.

Alimenté par les turns finalisés du LiveProcessor. À chaque déclenchement
(fin de tour / changement de locuteur, avec cooldown + forçage 2 min), appelle
live_advisor_mistral.suggest() EN THREAD DE FOND (ne bloque jamais l'ASR) et
accumule les suggestions, exposées au backend via get_suggestions().

Actif uniquement si un OBJECTIF est fourni ET MISTRAL_API_KEY est présente.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

# live_advisor_mistral.py est à la racine du projet.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


class LiveAdvisorWorker:
    def __init__(self, objectif: str, participants: str = "", entreprises: str = "",
                 session_id: str = "live", model: str = "mistral-small-latest"):
        self.objectif = (objectif or "").strip()
        self.participants = participants or ""
        self.entreprises = entreprises or ""
        self.session_id = session_id
        self.model = model
        self._recent: list[str] = []          # derniers turns "[spk]: texte"
        self._suggestions: list[dict] = []      # [{ts, items:[str,...]}]
        self._lock = threading.Lock()
        self._busy = False
        self._trigger = None
        self._suggest = None
        self.active = False

        if not self.objectif or not os.environ.get("MISTRAL_API_KEY", "").strip():
            return
        try:
            from live_advisor_mistral import suggest, LiveTrigger
            self._suggest = suggest
            self._trigger = LiveTrigger(cooldown_s=6.0, max_gap_s=120.0)
            self.active = True
        except Exception as exc:
            print(f"[LIVE][ADVISOR] import KO : {exc}", file=sys.stderr)
            self.active = False

    # ---- alimenté par le LiveProcessor à chaque turn finalisé ------------
    def on_turn(self, speaker: str, text: str, *, is_final: bool = True) -> None:
        if not self.active:
            return
        text = (text or "").strip()
        if not text:
            return
        with self._lock:
            self._recent.append(f"[{speaker or '?'}]: {text}")
            self._recent = self._recent[-20:]
        # is_other=True : sur flux mixte on conseille sur toute la conversation.
        if self._trigger.should_fire(now=time.time(), speaker=speaker,
                                     is_other=True, segment_finalized=is_final):
            self._fire()

    def _fire(self) -> None:
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            with self._lock:
                turns = "\n".join(self._recent[-12:])
                prev = [s for grp in self._suggestions[-4:] for s in grp["items"]]
            items = self._suggest(
                turns, previous=prev, goal=self.objectif,
                api_key=os.environ.get("MISTRAL_API_KEY", ""),
                model=self.model, session_id=self.session_id, max_suggestions=3)
            if items:
                with self._lock:
                    self._suggestions.append({"ts": time.time(), "items": items})
                    self._suggestions = self._suggestions[-30:]
        except Exception as exc:
            print(f"[LIVE][ADVISOR] suggest KO : {exc}", file=sys.stderr)
        finally:
            self._busy = False

    # ---- lu par le backend (GET /api/record/suggestions) -----------------
    def get_suggestions(self) -> list[dict]:
        with self._lock:
            return list(self._suggestions)
