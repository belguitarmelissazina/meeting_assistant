"""Compte rendu LOCAL — architecture orchestrateur agentique V8 (Ministral 3B).

Remplace l'ancien moteur local (meeting_minutes_pipeline, extraction 1-passe) par
l'ORCHESTRATEUR AGENTIQUE V8 : Context Builder -> Planner -> Content Designer ->
Workers de rédaction + juges déterministes, entièrement en Ministral 3B sur le
llama-server local (le même que gère déjà l'appli via Config).

Interface CLI IDENTIQUE à l'ancien moteur (le backend appelle la sous-commande
`minutes` avec ces mêmes flags — voir backend/run_app.py) :
    minutes --transcript T.txt --output R.md [--participants "..."] [--entreprises "..."]

En interne : appelle `_bench_orchestrator.run(...)` en configuration V8
(modèle Ministral 3B par défaut, AUCUN routage par agent, PAS de speculative
decoding, PAS d'anonymisation → speaker mapping + entités figées actifs), dans un
dossier de travail, puis copie le compte rendu produit vers --output.

NB : l'orchestrateur est lent (agentique, 3B local) — plusieurs dizaines de
minutes selon la durée de la réunion. Le backend n'impose aucun timeout.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compte rendu local via orchestrateur agentique V8 (Ministral 3B).")
    ap.add_argument("--transcript", required=True, help="Transcript normalisé (.txt)")
    ap.add_argument("--output", required=True, help="Compte rendu .md à écrire")
    ap.add_argument("--participants", default=None)
    ap.add_argument("--entreprises", default=None)
    args = ap.parse_args()

    participants = (args.participants if args.participants is not None
                    else os.environ.get("MEETING_PARTICIPANTS", "")).strip()
    entreprises = (args.entreprises if args.entreprises is not None
                   else os.environ.get("MEETING_ENTREPRISES", "")).strip()

    transcript_path = Path(args.transcript)
    output_path = Path(args.output)
    if not transcript_path.exists():
        print(f"ERROR: transcript introuvable : {transcript_path}", file=sys.stderr)
        sys.exit(1)

    # Dossier de travail de l'orchestrateur = dossier du compte rendu final.
    work_dir = output_path.parent
    work_dir.mkdir(parents=True, exist_ok=True)

    # Import différé (tire meeting_minutes_pipeline : numpy/scipy/llama-server).
    from _bench_orchestrator import run as orchestrate

    print("[local-minutes] orchestrateur agentique V8 (Ministral 3B) — démarrage")
    rc = orchestrate(
        transcript_path=transcript_path,
        sections_path=None,        # run complet (pas de reprise de sections)
        participants=participants,
        entreprises=entreprises,
        output_dir=work_dir,
        agentic_model=None,        # V8 : Ministral 3B par défaut (Config)
        context_model=None,        # aucun routage par agent
        worker_model=None,
        draft_model=None,          # pas de speculative decoding
        anonyme=False,             # V8 nommé : speaker mapping + entités figées
    )
    if rc != 0:
        print(f"ERROR: orchestrateur a échoué (code {rc})", file=sys.stderr)
        sys.exit(rc or 1)

    produced = work_dir / "compte_rendu_v4.md"
    if not produced.exists():
        print(f"ERROR: compte rendu non produit : {produced}", file=sys.stderr)
        sys.exit(1)
    if produced.resolve() != output_path.resolve():
        shutil.copyfile(produced, output_path)
    print(f"[local-minutes] écrit -> {output_path}")


if __name__ == "__main__":
    main()
