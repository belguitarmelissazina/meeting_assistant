"""Suivi d'expériences MLflow pour les pipelines de compte rendu.

Réutilisable par TOUTES les architectures (Mistral API pure, hybride local+API).
Chaque exécution = 1 run MLflow taggé `architecture`, qui logge :
  - params : architecture, modèles par étape, config
  - par ÉTAPE : temps, tokens input, tokens output, tokens cachés, nb d'appels, COÛT
  - global : tokens in/out totaux, temps total, COÛT total
  - artefacts : prompts (1 template/étape), CR résultat, breakdown.json, pricing_used.json

Le COÛT est calculé via une table de prix par modèle (input / output / input caché
à ~10% / rabais batch -50%). Le local a un coût API nul mais on garde tokens+temps.

Comparaison dans l'UI MLflow :  mlflow ui   puis comparer les runs sur
`total.cost_usd`, `extraction.cost_usd`, `redaction.cost_usd`, ...

Dépendance :  pip install mlflow   (importée paresseusement : ce module s'importe
sans mlflow ; seul Tracker(...) en a besoin).
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path

# Même montage que le projet diarisation (speaker-diarization-transcription) :
# backend SQLite (supporté par MLflow ; le file store mlruns/ brut est en
# "maintenance mode" depuis 3.14 et lève une exception) + artefacts dans ./mlruns.
# Le pipeline ET `mlflow ui` doivent viser le MÊME mlflow.db (voir mlflow_ui.py).
_REPO = Path(__file__).resolve().parent
MLFLOW_DB_URI = f"sqlite:///{(_REPO / 'mlflow.db').as_posix()}"
ARTIFACT_ROOT = _REPO / "mlruns"


# ===========================================================================
# TABLE DE PRIX — USD / 1 MILLION de tokens.  ⚠️ À VÉRIFIER / METTRE À JOUR
# sur les pages officielles (https://mistral.ai/pricing). Valeurs éditables ici.
#   input        : tokens d'entrée « frais »
#   cached_input : tokens d'entrée servis par le prompt caching (Mistral ~10%)
#   output       : tokens de sortie
# ===========================================================================
PRICING: dict[str, dict[str, float]] = {
    # Prix officiels mistral.ai (relevés manuellement). cached_input = 10% de input
    # (prompt caching Mistral). NB : le prix suit le positionnement (open vs
    # propriétaire), PAS la taille -> Medium 3.5 (propriétaire) > Large 3 (open).
    "mistral-large-latest":  {"input": 0.50, "cached_input": 0.05,  "output": 1.50},  # Large 3 (open-weight)
    "mistral-small-latest":  {"input": 0.15, "cached_input": 0.015, "output": 0.60},  # Small 4 (open, Apache 2.0)
    "mistral-medium-latest": {"input": 1.50, "cached_input": 0.15,  "output": 7.50},  # Medium 3.5 (propriétaire, SOTA/entreprise)
    "voxtral-mini-latest":   {"input": 0.0,  "cached_input": 0.0,   "output": 0.0},
    # Modèles LOCAUX (llama.cpp) : coût API nul (tokens/temps suivis quand même).
    "local":                 {"input": 0.0,  "cached_input": 0.0,   "output": 0.0},
    "ministral-3b-local":    {"input": 0.0,  "cached_input": 0.0,   "output": 0.0},
}
BATCH_DISCOUNT = 0.5  # -50 % en mode Batch API


def price_call(model: str, in_tok: int, out_tok: int,
               cached_in: int = 0, batch: bool = False) -> float:
    """Coût en USD d'un appel. cached_in = tokens d'entrée servis par le cache."""
    p = PRICING.get(model, PRICING["local"])
    non_cached_in = max(0, in_tok - cached_in)
    cost = (
        non_cached_in * p["input"]
        + cached_in * p["cached_input"]
        + out_tok * p["output"]
    ) / 1_000_000
    if batch:
        cost *= (1 - BATCH_DISCOUNT)
    return cost


class Tracker:
    """Un run MLflow par exécution d'architecture. Accumule les métriques par étape."""

    def __init__(self, architecture: str, config: dict | None = None,
                 experiment: str = "meeting-cr", run_name: str | None = None,
                 tracking_uri: str | None = None):
        import mlflow  # import paresseux
        self.mlflow = mlflow
        # Backend SQLite fixe (indépendant du dossier courant). Le pipeline ET
        # `mlflow ui` visent le même mlflow.db ; artefacts rootés dans ./mlruns.
        if not tracking_uri:
            tracking_uri = MLFLOW_DB_URI
        mlflow.set_tracking_uri(tracking_uri)
        print(f"[MLflow] store = {mlflow.get_tracking_uri()}")
        if mlflow.get_experiment_by_name(experiment) is None:
            ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            mlflow.create_experiment(experiment,
                                     artifact_location=ARTIFACT_ROOT.as_uri())
        mlflow.set_experiment(experiment)
        self.run = mlflow.start_run(run_name=run_name or architecture)
        self.architecture = architecture
        # name -> agrégat de l'étape
        self.steps: dict[str, dict] = {}
        self._t0 = time.time()
        self._prompts_logged: set[str] = set()

        mlflow.set_tag("architecture", architecture)
        mlflow.log_param("architecture", architecture)
        for k, v in (config or {}).items():
            mlflow.log_param(k, v)

    # ---- Enregistrement d'un appel LLM -----------------------------------
    def log(self, step: str, model: str, in_tok: int, out_tok: int,
            latency: float, prompt: str | None = None,
            cached_in: int = 0, batch: bool = False) -> float:
        cost = price_call(model, in_tok, out_tok, cached_in, batch)
        s = self.steps.setdefault(step, {
            "calls": 0, "input_tokens": 0, "output_tokens": 0,
            "cached_input_tokens": 0, "latency_s": 0.0, "cost_usd": 0.0,
            "model": model, "batch": batch,
        })
        s["calls"] += 1
        s["input_tokens"] += in_tok
        s["output_tokens"] += out_tok
        s["cached_input_tokens"] += cached_in
        s["latency_s"] += latency
        s["cost_usd"] += cost
        s["model"] = model
        if prompt and step not in self._prompts_logged:
            self.mlflow.log_text(prompt, f"prompts/{step}.txt")
            self._prompts_logged.add(step)
        return cost

    @contextmanager
    def step(self, name: str, model: str, batch: bool = False):
        """Chronomètre un appel. Renseigne le handle dans le bloc :
            with tk.step("extraction", "mistral-small-latest", batch=True) as h:
                resp = call(...)
                h["in"], h["out"] = resp.usage.prompt_tokens, resp.usage.completion_tokens
                h["cached_in"] = getattr(resp.usage, "cached_tokens", 0) or 0
                h["prompt"] = prompt
        """
        t0 = time.time()
        h = {"in": 0, "out": 0, "cached_in": 0, "prompt": None}
        try:
            yield h
        finally:
            self.log(name, model, int(h["in"]), int(h["out"]),
                     time.time() - t0, h.get("prompt"),
                     int(h.get("cached_in") or 0), batch)

    # ---- Artefacts intermédiaires (une sortie par étape) -----------------
    def artifact_json(self, obj, path: str) -> None:
        """Logue un objet (dict OU list) en JSON dans les artefacts du run.
        Ex: tk.artifact_json(plan, "steps/4_plan_sections.json")."""
        self.mlflow.log_dict(obj, path)

    def artifact_text(self, text: str, path: str) -> None:
        """Logue du texte brut (ex: prompt réellement envoyé) dans les artefacts."""
        self.mlflow.log_text(text or "", path)

    # ---- Clôture : métriques globales + artefacts ------------------------
    def finish(self, result_text: str | None = None,
               result_name: str = "compte_rendu.md",
               extra_artifacts: list | None = None) -> dict:
        mlflow = self.mlflow
        tot_in = sum(s["input_tokens"] for s in self.steps.values())
        tot_out = sum(s["output_tokens"] for s in self.steps.values())
        tot_cost = sum(s["cost_usd"] for s in self.steps.values())
        tot_lat = time.time() - self._t0

        # modèles par étape (param lisible)
        mlflow.log_param("models_by_step",
                         {k: v["model"] for k, v in self.steps.items()})

        for name, s in self.steps.items():
            mlflow.log_metric(f"{name}.input_tokens", s["input_tokens"])
            mlflow.log_metric(f"{name}.output_tokens", s["output_tokens"])
            mlflow.log_metric(f"{name}.cached_input_tokens", s["cached_input_tokens"])
            mlflow.log_metric(f"{name}.calls", s["calls"])
            mlflow.log_metric(f"{name}.latency_s", round(s["latency_s"], 2))
            mlflow.log_metric(f"{name}.cost_usd", round(s["cost_usd"], 6))

        mlflow.log_metric("total.input_tokens", tot_in)
        mlflow.log_metric("total.output_tokens", tot_out)
        mlflow.log_metric("total.cost_usd", round(tot_cost, 6))
        mlflow.log_metric("total.latency_s", round(tot_lat, 2))

        mlflow.log_dict({
            "architecture": self.architecture,
            "steps": {n: {**s, "cost_usd": round(s["cost_usd"], 6),
                          "latency_s": round(s["latency_s"], 2)}
                      for n, s in self.steps.items()},
            "total": {"input_tokens": tot_in, "output_tokens": tot_out,
                      "cost_usd": round(tot_cost, 6), "latency_s": round(tot_lat, 2)},
        }, "breakdown.json")
        mlflow.log_dict(PRICING, "pricing_used.json")

        if result_text is not None:
            mlflow.log_text(result_text, f"result/{result_name}")
        for path in (extra_artifacts or []):
            mlflow.log_artifact(str(path))

        mlflow.end_run()

        # récap console
        print(f"\n[MLflow] architecture={self.architecture}")
        for n, s in self.steps.items():
            print(f"  {n:14s} calls={s['calls']:2d}  in={s['input_tokens']:6d}  "
                  f"out={s['output_tokens']:6d}  {s['latency_s']:6.1f}s  "
                  f"${s['cost_usd']:.4f}")
        print(f"  {'TOTAL':14s}          in={tot_in:6d}  out={tot_out:6d}  "
              f"{tot_lat:6.1f}s  ${tot_cost:.4f}")
        return {"input_tokens": tot_in, "output_tokens": tot_out,
                "cost_usd": tot_cost, "latency_s": tot_lat}
