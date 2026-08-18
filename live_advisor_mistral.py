"""Live advisor v2 — conseiller temps réel via l'API Mistral (basse latence).

Refonte de l'advisor du projet audio : au lieu de 3-7 cartes riches générées en
local, on produit une simple LISTE de SUGGESTIONS / RECOMMANDATIONS courtes
(pistes, angles, points à clarifier, prochaines étapes) — PAS la phrase exacte à
dire, PAS de système de cards.

Optimisations latence :
  - Le CONSTANT (objectif, style, interdits) est dans le SYSTEM prompt, mis en
    cache Mistral (prompt_cache_key = session) -> resservi ~gratis.
  - Le VARIABLE (derniers échanges + état court + déjà-suggéré) est minimal.
  - Sortie minuscule : une liste de chaînes. Modèle rapide -> ~1 s / appel.

Déclenchement (à câbler dans la boucle live) : sur FIN DE TOUR (segment ASR
finalisé sur silence, ou changement de locuteur), éventuellement filtré aux
QUESTIONS via looks_like_question(). Voir helpers en bas.

Usage (démo / test) :
    MISTRAL_API_KEY=sk-xxx python live_advisor_mistral.py \
        --transcript dicte_audio_3.normalized.txt --turns 12 \
        --goal "Comprendre les besoins IA de RTE et faire avancer un POC"

Intégration : appeler suggest(...) -> list[str], remplace generate_suggestions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"
TIMEOUT_S = 60


SYS_TEMPLATE = """Tu es un CONSEILLER en temps réel pendant une réunion / un entretien.
À partir des derniers échanges, tu proposes des SUGGESTIONS et RECOMMANDATIONS
courtes et actionnables pour aider l'utilisateur à atteindre son objectif.
Réponds UNIQUEMENT en JSON.

OBJECTIF DE L'UTILISATEUR : {goal}
STYLE ATTENDU : {style}
À NE PAS FAIRE : {do_not_do}

CE QUE TU PROPOSES = des RECOMMANDATIONS (PAS la phrase exacte à dire, PAS un
dialogue mot-à-mot) : pistes ou angles à explorer, points à clarifier, questions
à creuser, risques / signaux à adresser, prochaines étapes stratégiques.

RÈGLES :
- 1 à 3 suggestions MAXIMUM, les plus utiles MAINTENANT. Qualité > quantité.
- Chaque suggestion = UNE ligne, concise et actionnable (une recommandation).
- Ne te répète pas : des suggestions déjà faites te sont fournies.
- Base-toi UNIQUEMENT sur ce qui a été réellement dit. N'invente rien.
- Respecte le style et les interdits.

FORMAT (rien d'autre) :
{{"suggestions": ["...", "..."]}}"""


def build_system(goal: str, style: str, do_not_do: list[str]) -> str:
    return SYS_TEMPLATE.format(
        goal=goal or "(non précisé)",
        style=style or "professionnel, concis",
        do_not_do="; ".join(do_not_do) if do_not_do else "(aucun)",
    )


def _mistral_json(system: str, user: str, api_key: str, model: str,
                  cache_key: str | None = None, timeout: int = TIMEOUT_S) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    if cache_key:
        payload["prompt_cache_key"] = cache_key
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        MISTRAL_URL, data=data, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Mistral HTTP {e.code}: {e.read().decode('utf-8', 'replace')}") from e
    content = res["choices"][0]["message"]["content"].strip()
    try:
        return json.loads(content)
    except Exception:
        import re
        m = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(m.group(0)) if m else {"suggestions": []}


def suggest(last_turns: str,
            state_summary: str = "",
            previous: list[str] | None = None,
            *,
            goal: str = "",
            style: str = "professionnel, concis",
            do_not_do: list[str] | None = None,
            api_key: str | None = None,
            model: str = DEFAULT_MODEL,
            session_id: str | None = None,
            max_suggestions: int = 3) -> list[str]:
    """Retourne 1 à `max_suggestions` recommandations concises (liste de chaînes).

    last_turns   : derniers échanges (texte, format "[locuteur]: ...").
    state_summary: mémoire courte (facultatif).
    previous     : suggestions déjà proposées (anti-répétition).
    goal/style/do_not_do : la SessionPolicy (constants -> cachés dans le system).
    session_id   : clé de cache Mistral (system identique sur la session).
    """
    api_key = (api_key or os.environ.get("MISTRAL_API_KEY", "")).strip()
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY manquante")
    previous = previous or []

    system = build_system(goal, style, do_not_do or [])
    prev_txt = "\n".join(f"- {p}" for p in previous[-8:]) or "(aucune)"
    user = (
        f"ÉCHANGES RÉCENTS :\n{last_turns}\n\n"
        f"CONTEXTE (mémoire courte) : {state_summary or '(début de réunion)'}\n\n"
        f"DÉJÀ SUGGÉRÉ (ne pas répéter) :\n{prev_txt}"
    )

    raw = _mistral_json(system, user, api_key, model,
                        cache_key=(f"advisor-{session_id}" if session_id else "advisor"))
    out: list[str] = []
    seen = {p.strip().lower() for p in previous}
    for s in (raw.get("suggestions") or []):
        s = (s if isinstance(s, str) else str(s.get("suggestion", "") if isinstance(s, dict) else "")).strip()
        if not s or s.lower() in seen:
            continue
        out.append(s)
        seen.add(s.lower())
        if len(out) >= max_suggestions:
            break
    return out


# ---------------------------------------------------------------------------
# Helpers de déclenchement (à utiliser dans la boucle live)
# ---------------------------------------------------------------------------
_Q_WORDS = (
    "est-ce que", "est ce que", "qu'est", "qu est", "c'est quoi", "comment",
    "pourquoi", "quel", "quelle", "quels", "quelles", "qui", "quand", "combien",
    "où", "peux-tu", "pouvez-vous", "pourriez", "pourrais", "avez-vous", "as-tu",
)


def looks_like_question(text: str) -> bool:
    """Heuristique rapide (pas d'appel LLM) : le texte est-il une question ?"""
    t = text.strip().lower()
    if not t:
        return False
    if t.endswith("?"):
        return True
    head = t[:45]
    return any(head.startswith(w) or (" " + w) in head for w in _Q_WORDS)


def is_end_of_turn(prev_speaker: str | None, cur_speaker: str | None,
                   segment_finalized: bool) -> bool:
    """Fin de tour = segment ASR finalisé (silence détecté par le VAD) OU
    changement de locuteur. Le streaming_transcriber fournit ces deux infos."""
    return bool(segment_finalized) or (prev_speaker is not None
                                       and cur_speaker != prev_speaker)


class LiveTrigger:
    """Contrôleur de déclenchement de l'advisor pendant la réunion.

    Déclenche quand l'AUTRE vient de parler ET (fin de tour OU changement de
    locuteur), avec un cooldown anti-spam. Filet de sécurité : si `max_gap_s`
    (défaut 120 s = 2 min) s'écoulent sans aucun déclenchement, on FORCE un tir.

    `is_other` doit être fourni par l'appelant : en visio, micro = moi et
    loopback (son des HP) = les autres, donc is_other = (source == "loopback").
    """

    def __init__(self, cooldown_s: float = 6.0, max_gap_s: float = 120.0):
        self.cooldown_s = cooldown_s
        self.max_gap_s = max_gap_s
        self._last_fire = 0.0
        self._last_speaker: str | None = None

    def should_fire(self, *, now: float, speaker: str | None = None,
                    is_other: bool = True, segment_finalized: bool = True) -> bool:
        gap = now - self._last_fire
        speaker_changed = self._last_speaker is not None and speaker != self._last_speaker
        self._last_speaker = speaker

        # 1) Filet de sécurité : 2 min sans rien -> on force (même si c'est moi).
        if gap >= self.max_gap_s:
            self._last_fire = now
            return True
        # 2) Anti-spam.
        if gap < self.cooldown_s:
            return False
        # 3) On ne conseille que sur les tours de l'AUTRE.
        if not is_other:
            return False
        # 4) Fin de tour (silence) ou changement de locuteur.
        if segment_finalized or speaker_changed:
            self._last_fire = now
            return True
        return False


# ---------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # console Windows = cp1252 -> force UTF-8
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Démo live advisor Mistral (recommandations concises).")
    ap.add_argument("--transcript", type=Path, required=True)
    ap.add_argument("--turns", type=int, default=12, help="Nb de dernières lignes envoyées")
    ap.add_argument("--goal", default="Comprendre les besoins du client et faire avancer un POC")
    ap.add_argument("--style", default="professionnel, concis")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    _load_dotenv(Path(__file__).resolve().parent / ".env")
    if not os.environ.get("MISTRAL_API_KEY", "").strip():
        print("ERROR: MISTRAL_API_KEY manquante", file=sys.stderr)
        return 2

    lines = [ln.strip() for ln in args.transcript.read_text(encoding="utf-8").splitlines() if ln.strip()]
    last_turns = "\n".join(lines[-args.turns:])

    t0 = time.time()
    sugg = suggest(last_turns, goal=args.goal, style=args.style,
                   model=args.model, session_id="demo")
    dt = time.time() - t0

    print(f"[live-advisor] {len(sugg)} suggestion(s) en {dt:.2f}s (modèle={args.model})\n")
    for i, s in enumerate(sugg, 1):
        print(f"{i}. {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
