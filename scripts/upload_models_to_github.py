"""Upload des modèles ML vers une release du repo GitHub PRIVÉ existant
`meeting-assistant-releases` (le même que celui des installeurs).

But : héberger les modèles sur GitHub Releases (whitelist entreprise quasi
universelle) au lieu de HuggingFace (bloqué chez beaucoup de grands comptes
type RTE, EDF, BNP). Le downloader.js de l'app tape sur GitHub en PRIMAIRE
(avec le READ token déjà embarqué) et retombe sur HF en fallback si jamais.

Pourquoi le MÊME repo que les installeurs : pas de redistribution publique
des modèles tiers (HF), réutilisation du READ token déjà gravé dans
app-update.yml, pas de nouveau repo à créer.

Pré-requis :
  1. Avoir créé une release vide dans `meeting-assistant-releases` avec
     le tag `assets-v1` :
     https://github.com/belguitarmelissazina/meeting-assistant-releases/releases/new
     (la release n'interfère pas avec l'auto-updater de l'app qui ne lit
     que `latest.yml`, présent uniquement sur les releases v0.x.y.)
  2. Avoir le GH_TOKEN WRITE (= celui de electron/.env) qui a déjà
     Contents read+write sur ce repo.
  3. Avoir les modèles téléchargés localement (Meeting Assistant déjà
     lancé une fois sur cette machine).

Usage :
    python scripts/upload_models_to_github.py

Le script lit automatiquement le GH_TOKEN depuis electron/.env (le même
fichier qui sert à `npm run publish`). Si tu veux override, tu peux toujours
poser $env:GH_TOKEN avant de lancer.

Idempotent : un asset homonyme est supprimé puis ré-uploadé. Tu peux
relancer le script sans risque.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OWNER = "belguitarmelissazina"
REPO = "meeting-assistant-releases"
RELEASE_TAG = "assets-v1"

# Chemin vers electron/.env (relatif au repo). C'est là que vivent les jetons
# GH_TOKEN (write) et GH_READ_TOKEN (read), gitignorés, utilisés par
# `npm run publish` et maintenant par ce script.
ENV_FILE = Path(__file__).resolve().parent.parent / "electron" / ".env"


def _load_env_file(path: Path) -> None:
    """Parser .env minimal (KEY=value, support des guillemets, commentaires #).
    Pose les variables dans os.environ en ÉCRASANT toute valeur existante :
    pour ce script, `.env` est la source de vérité. Sinon piège classique :
    une vieille variable d'env de session (genre placeholder oublié) fait
    silencieusement échouer le script."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value

# Source LOCALE : ton install Meeting Assistant a déjà les modèles ici.
# Si tu lances le script sur une autre machine, change ce chemin ou copie
# le dossier `assets/` depuis ton poste principal.
LOCAL_ASSETS = (
    Path(os.environ.get("APPDATA", "")) / "Meeting Assistant" / "assets"
)

# (chemin LOCAL sous `assets/`, nom de l'asset sur GitHub)
# Le nom de l'asset DOIT matcher ce qu'attend electron/model_manifest.js.
UPLOADS: list[tuple[str, str]] = [
    # LLM Mistral
    ("models/mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
     "mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"),
    # Sherpa ASR FR
    ("sherpa-onnx-streaming-zipformer-fr-kroko/encoder.onnx", "sherpa-encoder.onnx"),
    ("sherpa-onnx-streaming-zipformer-fr-kroko/decoder.onnx", "sherpa-decoder.onnx"),
    ("sherpa-onnx-streaming-zipformer-fr-kroko/joiner.onnx",  "sherpa-joiner.onnx"),
    ("sherpa-onnx-streaming-zipformer-fr-kroko/tokens.txt",   "sherpa-tokens.txt"),
    # WeSpeaker (diarisation)
    ("pretrained_models/resnet34/voxceleb_resnet34_LM.onnx", "voxceleb_resnet34_LM.onnx"),
    # MiniLM (sentence-transformers) — préfixe `minilm-` pour éviter les
    # collisions de noms type config.json qui existe dans plein de modèles.
    ("models_hf/all-MiniLM-L6-v2/config.json",                       "minilm-config.json"),
    ("models_hf/all-MiniLM-L6-v2/config_sentence_transformers.json", "minilm-config_sentence_transformers.json"),
    ("models_hf/all-MiniLM-L6-v2/modules.json",                      "minilm-modules.json"),
    ("models_hf/all-MiniLM-L6-v2/sentence_bert_config.json",         "minilm-sentence_bert_config.json"),
    ("models_hf/all-MiniLM-L6-v2/special_tokens_map.json",           "minilm-special_tokens_map.json"),
    ("models_hf/all-MiniLM-L6-v2/tokenizer.json",                    "minilm-tokenizer.json"),
    ("models_hf/all-MiniLM-L6-v2/tokenizer_config.json",             "minilm-tokenizer_config.json"),
    ("models_hf/all-MiniLM-L6-v2/vocab.txt",                         "minilm-vocab.txt"),
    ("models_hf/all-MiniLM-L6-v2/model.safetensors",                 "minilm-model.safetensors"),
    ("models_hf/all-MiniLM-L6-v2/1_Pooling/config.json",             "minilm-1_Pooling_config.json"),
]


def _api(method: str, url: str, token: str, *, body: bytes | None = None,
         content_type: str | None = None, accept: str = "application/vnd.github+json") -> tuple[int, bytes]:
    """Wrapper HTTP minimal pour GitHub API (pas de requests pour éviter deps)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "meeting-assistant-upload-script",
    }
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def get_release(token: str) -> dict:
    """Récupère la release par tag. Erreur si elle n'existe pas — l'utilisateur
    doit l'avoir créée manuellement (1 minute via l'UI GitHub)."""
    code, body = _api(
        "GET",
        f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{RELEASE_TAG}",
        token,
    )
    if code == 401:
        raise SystemExit(
            "HTTP 401 — jeton GH_TOKEN refusé par GitHub.\n"
            "Vérifie que :\n"
            "  1. Tu as mis la VRAIE valeur du jeton (pas le placeholder du tuto)\n"
            "  2. Le jeton n'est pas expiré (regarde sur github.com/settings/tokens)\n"
            "  3. Le jeton a bien Contents: Read and write sur le repo "
            f"{OWNER}/{REPO}"
        )
    if code == 404:
        raise SystemExit(
            f"Release '{RELEASE_TAG}' introuvable dans {OWNER}/{REPO} (HTTP 404).\n"
            f"Crée-la d'abord sur :\n"
            f"  https://github.com/{OWNER}/{REPO}/releases/new\n"
            f"avec le tag '{RELEASE_TAG}' (juste tag + Publier, pas de notes nécessaires)."
        )
    if code != 200:
        raise SystemExit(
            f"GitHub a refusé la requête (HTTP {code}).\n"
            f"Réponse brute : {body.decode('utf-8', errors='replace')[:300]}"
        )
    return json.loads(body)


def delete_existing_asset(token: str, release: dict, name: str) -> None:
    """Supprime un asset homonyme s'il existe déjà (rend l'upload idempotent)."""
    for a in release.get("assets", []) or []:
        if a.get("name") == name:
            code, _ = _api(
                "DELETE",
                f"https://api.github.com/repos/{OWNER}/{REPO}/releases/assets/{a['id']}",
                token,
            )
            if code not in (200, 204):
                raise SystemExit(f"Suppression échouée pour '{name}' (HTTP {code})")
            print(f"  ↺ ancien '{name}' supprimé pour re-upload")
            return


def upload_asset(token: str, release: dict, local_path: Path, asset_name: str) -> None:
    delete_existing_asset(token, release, asset_name)
    size = local_path.stat().st_size
    print(f"  ↥ upload {asset_name}  ({size / 1024 / 1024:.1f} Mo)…", flush=True)
    with local_path.open("rb") as f:
        data = f.read()
    code, body = _api(
        "POST",
        f"https://uploads.github.com/repos/{OWNER}/{REPO}/releases/{release['id']}"
        f"/assets?name={urllib.parse.quote(asset_name)}",
        token,
        body=data,
        content_type="application/octet-stream",
    )
    if code not in (200, 201):
        raise SystemExit(
            f"Upload échoué pour '{asset_name}' (HTTP {code}) : "
            f"{body.decode('utf-8', errors='replace')[:300]}"
        )
    print(f"     ✓ uploadé")


def main() -> None:
    # Charge automatiquement electron/.env (où GH_TOKEN est défini pour
    # `npm run publish`) — évite de devoir le copier-coller manuellement.
    _load_env_file(ENV_FILE)

    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            f"GH_TOKEN introuvable.\n"
            f"Vérifié :\n"
            f"  - Variable d'environnement GH_TOKEN : absente\n"
            f"  - Fichier .env : {ENV_FILE} {'(absent)' if not ENV_FILE.exists() else '(présent mais GH_TOKEN non défini dedans)'}\n"
            f"\n"
            f"Ajoute la ligne suivante à {ENV_FILE} :\n"
            f"  GH_TOKEN=github_pat_xxxxxxxxxxxxxxxxxxxxxx"
        )
    if not LOCAL_ASSETS.exists():
        raise SystemExit(
            f"Dossier modèles introuvable : {LOCAL_ASSETS}\n"
            f"Lance Meeting Assistant au moins une fois pour télécharger les modèles, "
            f"OU édite la constante LOCAL_ASSETS dans ce script."
        )
    print(f"Cible : https://github.com/{OWNER}/{REPO}/releases/tag/{RELEASE_TAG}")
    print(f"Source locale : {LOCAL_ASSETS}\n")

    # Vérif fichiers présents avant de commencer (échec rapide)
    missing = [rel for rel, _ in UPLOADS if not (LOCAL_ASSETS / rel).exists()]
    if missing:
        print("FICHIERS LOCAUX MANQUANTS :", file=sys.stderr)
        for m in missing:
            print(f"  ✗ {m}", file=sys.stderr)
        raise SystemExit("Lance d'abord l'app Meeting Assistant pour télécharger tous les modèles.")

    release = get_release(token)
    print(f"Release trouvée — id={release['id']}, "
          f"{len(release.get('assets') or [])} asset(s) déjà présent(s)\n")

    for rel_path, asset_name in UPLOADS:
        local_path = LOCAL_ASSETS / rel_path
        upload_asset(token, release, local_path, asset_name)

    total_gb = sum((LOCAL_ASSETS / r).stat().st_size for r, _ in UPLOADS) / 1024**3
    print(f"\n✓ Tous les assets uploadés ({total_gb:.2f} Go au total).")
    print(f"  https://github.com/{OWNER}/{REPO}/releases/tag/{RELEASE_TAG}")


if __name__ == "__main__":
    main()
