"""Compte rendu de réunion via l'API Mistral — architecture v2 (validée).

Version RETENUE (la plus fidèle au transcript d'après l'audit v2 vs v3) :
  0. Découpage sémantique (cosine boundary, réutilise meeting_minutes_pipeline)
  1. EXTRACTION par chunk (résumé + décisions + actions), métadonnées injectées
  2. MÉMOIRE (agrégat, 0 LLM)
  3. SYNTHÈSE globale (type de réunion + objectif + résumé global)
  4. PLANNER (3-5 sections thématiques + chunks pertinents + brief scopé)
  5. RÉDACTION par section (mémoire partagée + synthèse + brief + passages bruts)
  6. TABLEAUX décisions / plan d'action (déterministe, depuis la mémoire)
  7. ASSEMBLAGE Markdown

Pas de MLflow ici (module de production) : le suivi d'expériences reste dans
`_bench_mistral_v2.py`. Ce module ne dépend que de `meeting_minutes_pipeline`
(déjà embarqué par l'appli) pour le découpage.

Usage :
    MISTRAL_API_KEY=sk-xxx python mistral_minutes.py \
        --transcript audio.normalized.txt --output compte_rendu.md \
        [--participants "Alice, Bob"] [--entreprises "Yele, RTE"]

Variables d'environnement (équivalentes / complémentaires aux flags) :
    MISTRAL_API_KEY      obligatoire
    MEETING_CONTEXT      contexte libre (lève les ambiguïtés de sigles)
    MEETING_PARTICIPANTS liste des participants
    MEETING_ENTREPRISES  liste des entreprises
    MISTRAL_MODEL        défaut "mistral-small-latest"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from meeting_minutes_pipeline import (
    Config, load_segments_from_transcript, build_windows, embed_windows,
    detect_topic_boundaries, build_topic_chunks,
)

DEFAULT_MODEL = "mistral-small-latest"
DEFAULT_BASE = "https://api.mistral.ai"
TARGET_CHUNKS = 5
MAX_CHUNK_CHARS = 20000
MIN_INTERVAL_S = 1.0
TEMPERATURE = 0.2

_API: dict = {}
_LAST = [0.0]


# ---------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _mistral(system: str, user: str, model: str, json_mode: bool,
             timeout: int = 300, max_retries: int = 6, cache_key: str | None = None) -> str:
    """Appel chat throttlé + retry (429/5xx). Retourne le contenu texte."""
    wait = _API["min_interval"] - (time.time() - _LAST[0])
    if wait > 0:
        time.sleep(wait)
    url = _API["base"].rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": _API["temperature"],
    }
    if cache_key:
        payload["prompt_cache_key"] = cache_key
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {_API['key']}"}
    last = None
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                _LAST[0] = time.time()
                res = json.loads(r.read().decode("utf-8"))
            return res["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            _LAST[0] = time.time()
            if e.code == 429 or 500 <= e.code < 600:
                ra = e.headers.get("Retry-After")
                delay = float(ra) if (ra and ra.replace(".", "").isdigit()) else min(60.0, 2.0 ** attempt)
                print(f"[mistral-minutes][RATE] {e.code} -> pause {delay:.0f}s", file=sys.stderr)
                time.sleep(delay); last = e; continue
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            delay = min(60.0, 2.0 ** attempt)
            print(f"[mistral-minutes][NET] {e} -> pause {delay:.0f}s", file=sys.stderr)
            time.sleep(delay); last = e; continue
    raise RuntimeError(f"Echec API Mistral : {last}")


def _json(content: str) -> dict:
    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(m.group(0)) if m else {}


def _md_cell(s) -> str:
    return str(s).replace("\n", " ").replace("|", "\\|").strip()


def _meta_block(participants: str, entreprises: str, contexte: str) -> str:
    """Métadonnées (participants/entreprises/contexte) injectées en tête des prompts."""
    lines = []
    if participants.strip():
        lines.append("PARTICIPANTS (noms officiels, vérité — à utiliser EXACTEMENT) : "
                     + participants.strip())
    if entreprises.strip():
        lines.append("ENTREPRISES / ORGANISATIONS présentes : " + entreprises.strip())
    if contexte.strip():
        lines.append("CONTEXTE (fourni par l'utilisateur, pour lever les ambiguïtés de sigles) : "
                     + contexte.strip())
    return ("\n".join(lines) + "\n\n") if lines else ""


def _coarse_chunks(segments, cfg, target, max_chars):
    windows = build_windows(segments, cfg.boundary_window_size)
    emb = embed_windows(windows, cfg.embedding_model, cfg.embedding_batch_size)
    bnd, _, sm = detect_topic_boundaries(emb, sigma=cfg.boundary_smoothing_sigma,
                                         percentile=cfg.boundary_percentile,
                                         min_distance=cfg.boundary_min_distance)
    if target and len(bnd) > target - 1:
        bnd = sorted(sorted(bnd, key=lambda b: sm[b])[:target - 1])
    return build_topic_chunks(segments, windows, bnd, max_chars, cfg)


# ---------------------------------------------------------------------------
# Prompts (identiques à l'archi v2 validée)
# ---------------------------------------------------------------------------
SYS_EXTRACT = (
    "Tu extrais des informations d'un extrait de réunion. Réponds UNIQUEMENT en JSON. "
    "Règle : RIEN SI RIEN (tableaux vides si aucune décision/action). Une DÉCISION = "
    "un choix ACTÉ en séance (pas un projet passé raconté, pas une discussion). Une "
    "ACTION = une tâche post-réunion (engagement ou suggestion). N'invente rien. "
    "Des métadonnées (participants, entreprises) peuvent être fournies : pour désigner "
    "une personne, utilise EXACTEMENT un nom fourni si le contexte permet de l'identifier, "
    "sinon reste générique (« un intervenant ») ; ne reprends JAMAIS un label brut type "
    "SPEAKER_00 et n'invente aucun nom."
)
USR_EXTRACT = """{meta}Extrait :
{texte}

Produis ce JSON :
{{"resume": "3-5 phrases fidèles",
  "decisions": ["décision actée", ...],
  "actions": [{{"action":"...", "responsable":"nom fourni si identifiable, sinon —", "echeance":"— si absente"}}]}}"""

SYS_SYNTHESE = (
    "Tu établis le socle d'un compte rendu à partir des résumés de tous les passages. "
    "Réponds UNIQUEMENT en JSON. N'invente aucun nom : les participants te sont fournis. "
    "Choisis le TYPE de réunion le plus précis d'après la nature GLOBALE des échanges (pas "
    "un mot-clé isolé) ; les exemples fournis servent d'inspiration, tu n'es PAS obligé de "
    "t'y limiter."
)
USR_SYNTHESE = """Participants (vérité) : {participants}

Résumés des passages :
{memoire}

Pour le TYPE, voici des EXEMPLES pour t'inspirer (liste NON imposée, tu peux
en choisir un autre s'il est plus juste) :
prise de contact, avant-vente, réunion client, revue projet, point d'avancement,
brainstorm, atelier de travail, comité de pilotage, kick-off, démo, formation.

Classe d'après la nature DOMINANTE et l'intention réelle de la réunion, pas d'après
un mot isolé ni un sujet simplement évoqué en passant : distingue ce qui se passe
VRAIMENT en séance (présenter, décider, co-construire, suivre, démontrer...) de ce
qui n'est que mentionné pour plus tard.

Produis :
{{"type": "un seul type de réunion, le plus précis (inspiré des exemples ou autre)",
  "type_justification": "1 phrase citant les indices concrets du sommaire",
  "objectif": "1-2 phrases : le BUT de la réunion (distinct du type)",
  "resume_global": "paragraphe de 4-6 phrases, synthèse fidèle de l'ensemble"}}"""

SYS_PLANNER = (
    "Tu conçois le PLAN thématique de la section 'Sujets abordés' d'un compte rendu. "
    "Réponds UNIQUEMENT en JSON. Découpe en 3 à 5 sections thématiques DISTINCTES : ni "
    "une seule section fourre-tout, ni un thème par passage. Pour chaque section, choisis "
    "les chunk_ids pertinents (d'après les résumés) et écris un brief SCOPÉ qui dit ce que "
    "la section couvre ET ce qu'elle NE couvre PAS (déjà traité ailleurs), pour éviter les "
    "redites."
)
USR_PLANNER = """Contexte : {type} — {objectif}

Résumés par passage (chunk_id : résumé) :
{overview}

Produis :
{{"sections": [
   {{"titre":"Titre de section",
     "chunk_ids":[0,2],
     "brief":"Ce que couvre la section ; NE PAS inclure X (couvert ailleurs)."}}
]}}"""

SYS_REDACTION = (
    "Tu rédiges UNE section d'un compte rendu de réunion, en français, factuel, fidèle "
    "au texte fourni. Tu disposes de la MÉMOIRE PARTAGÉE (résumés de toute la réunion) et "
    "de la SYNTHÈSE GLOBALE pour la cohérence d'ensemble, mais tu ne rédiges QUE la "
    "section décrite par le brief (ne traite pas ce qui relève d'autres sections). "
    "N'invente rien. Ne mets pas de titre (il est ajouté séparément). Respecte le "
    "périmètre du brief. Ne développe pas les sigles. Des métadonnées (participants, "
    "entreprises) peuvent être fournies : pour nommer les intervenants, utilise EXACTEMENT "
    "ces noms quand le contexte permet de les identifier, sinon reste générique (« un "
    "intervenant »/« un participant ») ; ne reprends JAMAIS un label brut type SPEAKER_00 "
    "et n'invente aucun nom."
)
USR_REDACTION = """{meta}MÉMOIRE PARTAGÉE — résumés de tous les passages (vue d'ensemble, ne pas recopier) :
{memoire}

SYNTHÈSE GLOBALE (fil conducteur, ne pas recopier) :
{resume_global}

BRIEF DE TA SECTION :
{brief}

PASSAGES BRUTS DE TA SECTION (source de vérité) :
{chunks}

Rédige la section (1 à 3 paragraphes) :"""


# ---------------------------------------------------------------------------
def generate(transcript_path: Path, output_path: Path,
             participants: str, entreprises: str, contexte: str,
             api_key: str, model: str) -> None:
    _API.update(base=DEFAULT_BASE, key=api_key,
                min_interval=MIN_INTERVAL_S, temperature=TEMPERATURE)
    cfg = Config()
    meta = _meta_block(participants, entreprises, contexte)

    segments = load_segments_from_transcript(str(transcript_path))
    if not segments:
        raise ValueError(f"Transcript vide : {transcript_path}")
    chunks = _coarse_chunks(segments, cfg, TARGET_CHUNKS, MAX_CHUNK_CHARS)
    print(f"[mistral-minutes] modèle={model} | {len(segments)} segments -> {len(chunks)} chunks")
    # 1. EXTRACTION par chunk
    memory = []
    for ch in chunks:
        content = _mistral(SYS_EXTRACT, USR_EXTRACT.format(meta=meta, texte=ch.text),
                           model, json_mode=True, cache_key="extract")
        d = _json(content)
        memory.append({
            "chunk_id": ch.chunk_id,
            "resume": (d.get("resume") or "").strip(),
            "decisions": [x for x in (d.get("decisions") or []) if str(x).strip()],
            "actions": [a for a in (d.get("actions") or []) if isinstance(a, dict) and a.get("action")],
        })

    # 2. MÉMOIRE
    by_id = {c.chunk_id: c for c in chunks}
    overview = "\n".join(f"{m['chunk_id']} : {m['resume']}" for m in memory)
    memoire_txt = "\n".join(f"- {m['resume']}" for m in memory)

    # 3. SYNTHÈSE globale
    syn = _json(_mistral(SYS_SYNTHESE, USR_SYNTHESE.format(
        participants=participants or "(non fournis)", memoire=memoire_txt),
        model, json_mode=True))
    mtype = syn.get("type", "(non détecté)")
    objectif = syn.get("objectif", "")
    resume_global = syn.get("resume_global", "")

    # 4. PLANNER
    plan = (_json(_mistral(SYS_PLANNER, USR_PLANNER.format(
        type=mtype, objectif=objectif, overview=overview),
        model, json_mode=True)).get("sections")) or []

    # 5. RÉDACTION par section
    sections_md = []
    for i, sec in enumerate(plan, 1):
        titre = sec.get("titre", f"Section {i}")
        cids = [c for c in (sec.get("chunk_ids") or []) if c in by_id]
        brief = sec.get("brief", titre)
        chunks_txt = "\n\n".join(f"=== passage {c} ===\n{by_id[c].text}" for c in cids) or "(aucun passage)"
        body = _mistral(SYS_REDACTION, USR_REDACTION.format(
            meta=meta, memoire=memoire_txt, resume_global=resume_global,
            brief=brief, chunks=chunks_txt), model, json_mode=False, cache_key="redaction")
        sections_md.append((titre, body.strip()))

    # 6. TABLEAUX décisions / actions (déterministe)
    decisions, actions = [], []
    for m in memory:
        decisions += m["decisions"]
        actions += m["actions"]
    seen = set(); dec_u = []
    for d in decisions:
        k = " ".join(str(d).lower().split())
        if k not in seen:
            seen.add(k); dec_u.append(d)

    # 7. ASSEMBLAGE Markdown
    md = ["# Compte rendu de réunion", "", f"_Type de réunion_ : **{mtype}**", ""]
    if objectif:
        md += [f"_Objectif_ : {objectif}", ""]
    if participants.strip():
        md += [f"_Participants_ : {participants}", ""]
    if entreprises.strip():
        md += [f"_Entreprises_ : {entreprises}", ""]
    if resume_global:
        md += ["## Synthèse", "", resume_global, ""]
    md += ["## Sujets abordés", ""]
    for i, (titre, txt) in enumerate(sections_md, 1):
        md += [f"### {i}. {titre}", "", txt, ""]
    if dec_u:
        md += ["## Décisions", "", "| # | Décision |", "|---|---|"]
        md += [f"| {i} | {_md_cell(d)} |" for i, d in enumerate(dec_u, 1)] + [""]
    if actions:
        md += ["## Plan d'action", "", "| # | Action | Responsable | Échéance |",
               "|---|---|---|---|"]
        md += [f"| {i} | {_md_cell(a.get('action'))} | {_md_cell(a.get('responsable') or '—')} | {_md_cell(a.get('echeance') or '—')} |"
               for i, a in enumerate(actions, 1)] + [""]
    cr = "\n".join(md)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cr, encoding="utf-8")
    print(f"[mistral-minutes] écrit -> {output_path} ({len(cr)} chars, {len(sections_md)} sections)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Compte rendu via Mistral (architecture v2).")
    ap.add_argument("--transcript", required=True, help="Chemin du transcript normalisé (.txt)")
    ap.add_argument("--output", required=True, help="Chemin du compte rendu .md à écrire")
    ap.add_argument("--participants", default=None)
    ap.add_argument("--entreprises", default=None)
    args = ap.parse_args()

    _load_dotenv(Path(__file__).resolve().parent / ".env")
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not api_key:
        print("ERROR: MISTRAL_API_KEY manquante (variable d'environnement)", file=sys.stderr)
        sys.exit(2)

    participants = (args.participants if args.participants is not None
                    else os.environ.get("MEETING_PARTICIPANTS", "")).strip()
    entreprises = (args.entreprises if args.entreprises is not None
                   else os.environ.get("MEETING_ENTREPRISES", "")).strip()
    contexte = (os.environ.get("MEETING_CONTEXT", "") or "").strip()
    model = (os.environ.get("MISTRAL_MODEL", "") or DEFAULT_MODEL).strip()

    transcript_path = Path(args.transcript)
    output_path = Path(args.output)
    if not transcript_path.exists():
        print(f"ERROR: transcript introuvable : {transcript_path}", file=sys.stderr)
        sys.exit(1)

    try:
        generate(transcript_path, output_path, participants, entreprises,
                 contexte, api_key, model)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
