"""Lanceur de l'UI MLflow — même montage que le projet diarisation.

Usage :
    python mlflow_ui.py              # port 5000
    python mlflow_ui.py --port 5001  # autre port si 5000 est occupé

Pointe sur le MÊME backend SQLite que le pipeline (bench_tracking.py) :
diarisation-final/mlflow.db, artefacts dans diarisation-final/mlruns.
Aucune variable d'environnement à taper.
"""
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent
DB_URI = f"sqlite:///{(_REPO / 'mlflow.db').as_posix()}"


def main() -> int:
    args = sys.argv[1:]
    port = "5000"
    if "--port" in args:
        port = args[args.index("--port") + 1]

    print(f"[MLflow UI] backend = {DB_URI}")
    print(f"[MLflow UI] ouvre  http://localhost:{port}")
    cmd = [sys.executable, "-m", "mlflow", "ui",
           "--backend-store-uri", DB_URI,
           "--port", port]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
