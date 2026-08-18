#!/usr/bin/env python3
"""Runner Colab — orchestrateur agentique V9 avec UN SEUL modele 14B sur GPU.

Reutilise TEL QUEL l'architecture multi-agents de `_bench_orchestrator.py`
(+ `meeting_minutes_pipeline.py`) : extraction par chunk, Context Builder,
Planner, Content Designers, Workers/Juges, renderer markdown.

La SEULE difference avec un run local : le lancement de llama-server.
- Local (Windows/CPU)  : `llama-server.exe`, `-ngl 0`, threads CPU.
- Colab (Linux/GPU)    : binaire CUDA compile, `-ngl 99` (offload GPU complet).

On obtient ce comportement par MONKEYPATCH de `start_llm_server_slots`
(aucune modification des fichiers source n'est requise), puis on appelle
`run()` en ne fournissant QUE `--model` (= agentic_model). Comme
`--context-model` et `--worker-model` restent vides, `routing_actif` vaut
False et TOUTES les phases utilisent ce meme modele 14B.

Usage (depuis /content sur Colab) :
    python colab_run.py \
        --server-bin /content/llama.cpp/build/bin/llama-server \
        --model /content/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf \
        --transcript /content/mon_transcript.txt \
        --participants "Nom Prenom, Autre Nom" \
        --output-dir /content/out_14b \
        --ngl 99 --ctx 16384
"""
from __future__ import annotations

import argparse
import atexit
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import meeting_minutes_pipeline as mmp
import _bench_orchestrator as bench


def make_gpu_server_launcher(server_bin: str, n_gpu_layers: int, ctx: int):
    """Fabrique un remplacant GPU/Linux de `start_llm_server_slots`.

    Garde la meme signature (cfg, parallel_slots) pour etre un drop-in.
    Lit `cfg.llm_model_path` (defini par run()) et `cfg.llm_kv_cache_type`,
    mais impose le binaire CUDA, l'offload GPU et le ctx passes en argument.
    """

    def start_llm_server_slots_gpu(cfg, parallel_slots: int) -> None:
        # Libere le port si un serveur precedent traine (best-effort Linux).
        for tool in (["fuser", "-k", f"{cfg.llm_server_port}/tcp"],):
            try:
                subprocess.run(tool, capture_output=True)
            except Exception:
                pass

        if not Path(server_bin).exists():
            raise FileNotFoundError(f"llama-server introuvable : {server_bin}")
        if not Path(cfg.llm_model_path).exists():
            raise FileNotFoundError(f"Modele introuvable : {cfg.llm_model_path}")

        total_ctx = ctx if ctx > 0 else (cfg.llm_n_ctx or 16384)
        cmd = [
            server_bin,
            "-m", cfg.llm_model_path,
            "--port", str(cfg.llm_server_port),
            "--ctx-size", str(total_ctx),
            "--parallel", str(parallel_slots),
            "-ngl", str(n_gpu_layers),          # offload GPU (toutes les couches)
            "--flash-attn", "on",               # requis pour KV-cache quantifie
            "--cache-ram", "0",
            "--cache-type-k", cfg.llm_kv_cache_type,
            "--cache-type-v", cfg.llm_kv_cache_type,
            "--batch-size", "4096",
            "--ubatch-size", "1024",
            "--log-disable",
        ]
        print("[GPU] llama-server :", " ".join(cmd), flush=True)

        stderr_log = Path("_llama_server_stderr.log")
        fh = open(stderr_log, "w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=fh)

        # Confie le process au mecanisme de cleanup du pipeline : run() appelle
        # `_kill_server()` (importe de mmp) dans son finally, qui lit ce global.
        mmp._server_process = proc
        atexit.register(mmp._kill_server)

        health = f"http://{cfg.llm_server_host}:{cfg.llm_server_port}/health"
        deadline = time.time() + 600
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(health, timeout=2) as r:
                    if r.status == 200:
                        print("[GPU] llama-server pret", flush=True)
                        return
            except Exception:
                pass
            if proc.poll() is not None:
                fh.flush()
                tail = stderr_log.read_text(encoding="utf-8", errors="replace")[-3000:]
                raise RuntimeError(f"llama-server a crashe au demarrage :\n{tail}")
            time.sleep(1)
        raise TimeoutError("llama-server timeout au demarrage (600s)")

    return start_llm_server_slots_gpu


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--server-bin", required=True,
                    help="Binaire llama-server compile avec CUDA")
    ap.add_argument("--model", required=True,
                    help="GGUF 14B UNIQUE — utilise pour TOUTES les phases")
    ap.add_argument("--transcript", required=True,
                    help="Transcript normalise (.txt)")
    ap.add_argument("--participants", default=bench.DEFAULT_PARTICIPANTS,
                    help="Noms EXACTS des participants (speaker mapping + "
                         "entites figees anti-hallucination)")
    ap.add_argument("--entreprises", default="")
    ap.add_argument("--output-dir", default="out_14b")
    ap.add_argument("--ngl", type=int, default=99,
                    help="Couches offloadees au GPU (99 = tout)")
    ap.add_argument("--ctx", type=int, default=16384)
    args = ap.parse_args()

    # 1) Monkeypatch : lancement GPU au lieu de CPU/Windows. On remplace le
    #    nom dans les DEUX modules (ensure_model() de bench appelle le nom
    #    importe dans le namespace de bench).
    launcher = make_gpu_server_launcher(args.server_bin, args.ngl, args.ctx)
    bench.start_llm_server_slots = launcher
    mmp.start_llm_server_slots = launcher

    # 2) Run end-to-end. context_model/worker_model = None => modele unique.
    print(f"[INFO] Modele unique (toutes phases) : {Path(args.model).name}")
    print(f"[INFO] GPU offload -ngl={args.ngl} | ctx={args.ctx}")
    return bench.run(
        transcript_path=Path(args.transcript),
        sections_path=None,
        participants=args.participants,
        entreprises=args.entreprises,
        output_dir=Path(args.output_dir),
        agentic_model=Path(args.model),
        context_model=None,
        worker_model=None,
        draft_model=None,
    )


if __name__ == "__main__":
    sys.exit(main())
