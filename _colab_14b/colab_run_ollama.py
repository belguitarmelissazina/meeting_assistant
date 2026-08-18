#!/usr/bin/env python3
"""Runner Colab — orchestrateur agentique V9, modele UNIQUE, servi par OLLAMA (GPU).

Aucune modification des fichiers source. Tout passe par monkeypatch :

  - start_llm_server_slots -> no-op + health-check (Ollama tourne deja, il est
    lance dans le notebook ; il n'y a pas de llama-server.exe a demarrer).
  - llm_complete -> appelle l'endpoint NATIF d'Ollama `/api/chat` avec
    `format=<json_schema>`. C'est le point cle : sur `/v1/chat/completions`
    (compat OpenAI) Ollama IGNORE la syntaxe `response_format: json_schema`
    (cf. issue ollama#10001), alors que `format` sur `/api/chat` applique bien
    une grammaire derivee du schema. On garde donc la meme rigueur JSON que le
    serveur llama.cpp natif, sans build.

Le modele unique fait TOUTES les phases (context_model/worker_model = None,
donc routing_actif=False dans _bench_orchestrator).

Usage (depuis /content) :
    python colab_run_ollama.py \
        --model-name ministral \
        --transcript /content/dicte_audio_3.normalized.txt \
        --participants "Nom Prenom, Autre Nom" \
        --output-dir /content/out_ministral8b \
        --ctx 16384
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import meeting_minutes_pipeline as mmp
import _bench_orchestrator as bench

OLLAMA_URL = "http://127.0.0.1:11434"
_STATE = {"model": "ministral", "num_ctx": 16384, "num_predict": 0}


def ollama_complete(prompt, cfg, timeout: int = 300, json_schema: dict | None = None) -> str:
    """Remplacant de mmp.llm_complete via l'API native Ollama (schema fiable)."""
    options = {
        "temperature": cfg.llm_temperature,
        "top_k": 50,
        "repeat_penalty": cfg.llm_repeat_penalty,
        "num_ctx": _STATE["num_ctx"],
        "stop": ["<|end|>", "<|endoftext|>", "<|im_end|>", "</s>"],
    }
    # Plafond de tokens UNIQUEMENT si > 0 (filet anti-runaway, ne coupe pas le
    # contenu normal qui s'arrete bien avant). 0 = illimite (comportement Ollama
    # par defaut). NOTE: avec format, un cut renvoie un contenu vide -> fallback,
    # donc on garde une valeur large.
    if _STATE["num_predict"] and _STATE["num_predict"] > 0:
        options["num_predict"] = _STATE["num_predict"]
    payload = {
        "model": _STATE["model"],
        "messages": [
            {"role": "system", "content": mmp._build_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": options,
    }
    if json_schema is not None:
        payload["format"] = json_schema          # structured outputs natifs Ollama

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL + "/api/chat", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e

    # Surface les vraies erreurs Ollama (au lieu d'un 'Expecting value char 0'
    # opaque quand le contenu est vide).
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(f"Ollama error: {result['error']}")
    content = (result.get("message", {}).get("content") or "").strip()
    if not content:
        raise RuntimeError(
            f"Ollama a renvoye un contenu vide (done_reason="
            f"{result.get('done_reason')})"
        )
    return content


def noop_start(cfg, parallel_slots: int = 1) -> None:
    """Remplace start_llm_server_slots : Ollama est deja lance (par toi),
    on verifie juste qu'il repond et que le modele existe."""
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=5) as r:
            tags = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(
            "Ollama injoignable sur 127.0.0.1:11434 — lance d'abord 'ollama serve'."
        ) from e
    names = [m.get("name", "") for m in tags.get("models", [])]
    if not any(n.split(":")[0] == _STATE["model"] for n in names):
        raise RuntimeError(
            f"Modele Ollama '{_STATE['model']}' introuvable. Dispo : {names}"
        )
    print(f"[OLLAMA] OK — modele '{_STATE['model']}' pret (GPU)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-name", default="ministral",
                    help="Nom du modele cree dans Ollama (ollama create <nom>)")
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--sections", default=None,
                    help="sections.json existant -> SKIP l'extraction (reprend "
                         "directement aux agents/workers)")
    ap.add_argument("--participants", default=bench.DEFAULT_PARTICIPANTS)
    ap.add_argument("--entreprises", default="")
    ap.add_argument("--output-dir", default="out_ollama")
    ap.add_argument("--ctx", type=int, default=16384)
    ap.add_argument("--num-predict", type=int, default=0,
                    help="Plafond tokens/appel (0 = illimite, defaut). Mettre "
                         "4096+ comme filet anti-runaway si un worker boucle.")
    ap.add_argument("--no-speaker-mapping", action="store_true",
                    help="Desactive le speaker mapping (GARDE les participants "
                         "pour l'anti-hallucination + l'en-tete du CR)")
    a = ap.parse_args()
    _STATE["model"] = a.model_name
    _STATE["num_ctx"] = a.ctx
    _STATE["num_predict"] = a.num_predict

    # Monkeypatch dans LES DEUX modules (bench appelle les noms importes dans
    # son propre namespace ; mmp les appelle dans le sien).
    bench.start_llm_server_slots = noop_start
    mmp.start_llm_server_slots = noop_start
    bench.llm_complete = ollama_complete
    mmp.llm_complete = ollama_complete

    # Desactive le speaker mapping sans toucher aux participants : on neutralise
    # resolve_speaker_mapping (=> mapping vide => non applique). Les participants
    # restent epingles (entites anti-hallucination) et figurent en tete de CR.
    if a.no_speaker_mapping:
        mmp.resolve_speaker_mapping = lambda *x, **k: {}
        print("[INFO] Speaker mapping DESACTIVE (participants conserves)")

    print(f"[INFO] Backend = Ollama | modele unique '{a.model_name}' | ctx {a.ctx}")
    # agentic_model sert seulement de cle/label a ensure_model (aucun fichier
    # n'est charge cote serveur). context/worker = None => modele unique partout.
    return bench.run(
        transcript_path=Path(a.transcript),
        sections_path=Path(a.sections) if a.sections else None,
        participants=a.participants,
        entreprises=a.entreprises,
        output_dir=Path(a.output_dir),
        agentic_model=Path(a.model_name),
        context_model=None,
        worker_model=None,
        draft_model=None,
    )


if __name__ == "__main__":
    sys.exit(main())
