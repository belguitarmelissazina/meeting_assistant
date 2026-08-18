"""Multi-mode entry point for the packaged backend.

Usage:
    backend.exe                        # default: HTTP server (FastAPI)
    backend.exe server                 # HTTP server (FastAPI)
    backend.exe diar  -i AUDIO -o DIR  # diarisation + transcription pipeline
    backend.exe normalize IN.txt OUT.txt
    backend.exe minutes --transcript T.txt --output R.md [--participants ...]

PyInstaller produces a single `backend.exe` (frozen). Because the FastAPI
backend launches the heavy pipeline as subprocesses, those subprocesses also
need to invoke this same exe with a subcommand — frozen exes can't run
`python -m foo.bar` like a normal interpreter would. So this dispatcher
replaces all the previous `python -m diar_pipeline.run` / `python
normalize_transcript.py` / `python meeting_minutes_pipeline.py` invocations.

In dev (running through a regular Python interpreter), this script is also
the canonical way to start the backend — no behaviour difference.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Force single-threaded BLAS BEFORE numpy/scipy import — diarisation clustering
# (NMESC) is not deterministic under multithreaded MKL/OpenBLAS.
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
           "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

# Force UTF-8 sur stdout/stderr du backend, sinon Windows utilise cp1252
# par défaut et crashe sur tout caractère non-ASCII (ex. emojis dans nos
# logs, ou � produit par les subprocess quand on log leur stdout).
# Doit être fait AVANT tout import qui pourrait écrire (logging, etc).
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    # En frozen sans console attachée, sys.stdout peut être None/buffer-only
    # → on ignore, ce n'est pas critique.
    pass

# Ensure the project root is importable both in dev (script next to backend/)
# and in PyInstaller-frozen mode (bundle root).
if getattr(sys, "frozen", False):
    _ROOT = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
else:
    _ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _run_server() -> None:
    import uvicorn
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    # access_log=False : désactive le spam des GET /api/jobs/... toutes les
    # secondes (polling du frontend). Les erreurs sont loggées via le
    # middleware custom dans backend.main.
    uvicorn.run("backend.main:app", host=host, port=port,
                log_level="info", access_log=False)


def _run_diar(argv: list[str]) -> None:
    sys.argv = ["diar_pipeline.run", *argv]
    from diar_pipeline.run import main
    main()


def _run_normalize(argv: list[str]) -> None:
    sys.argv = ["normalize_transcript", *argv]
    from normalize_transcript import main
    main()


def _run_minutes(argv: list[str]) -> None:
    # Moteur LOCAL = orchestrateur agentique V8 (Ministral 3B), via l'adaptateur
    # local_minutes (même interface CLI que l'ancien meeting_minutes_pipeline).
    sys.argv = ["local_minutes", *argv]
    from local_minutes import main
    main()


def _run_mistral_minutes(argv: list[str]) -> None:
    sys.argv = ["mistral_minutes", *argv]
    from mistral_minutes import main
    main()


_DISPATCH = {
    "server":          _run_server,
    "diar":            _run_diar,
    "normalize":       _run_normalize,
    "minutes":         _run_minutes,
    "mistral-minutes": _run_mistral_minutes,
}


def main() -> None:
    args = sys.argv[1:]
    if not args:
        cmd, rest = "server", []
    else:
        cmd, rest = args[0], args[1:]
    handler = _DISPATCH.get(cmd)
    if handler is None:
        print(f"Unknown subcommand: {cmd!r}", file=sys.stderr)
        print(f"Valid: {', '.join(_DISPATCH)}", file=sys.stderr)
        sys.exit(2)
    if cmd == "server":
        handler()
    else:
        handler(rest)


if __name__ == "__main__":
    main()
