# Bench V9 hybride → modèle unique sur Google Colab (GPU)

Teste l'architecture agentique de `_bench_orchestrator.py` (bench **V9 hybride**)
avec **un seul modèle pour tout**, exécuté sur **GPU** au lieu du CPU local.

> ## 🅰️ / 🅱️ Deux variantes — choisis selon que tu veux compiler ou non
>
> | | Backend | Build ? | Fichiers | Reco |
> |---|---|---|---|---|
> | **🅰️ llama.cpp natif** | `llama-server` CUDA | ⚙️ compilation (~8 min, cacheable Drive) | notebook `colab_orchestrator_14b.ipynb` + `colab_run.py` | Comportement de référence, JSON strict garanti |
> | **🅱️ Ollama** | Ollama (= moteur llama.cpp) | ✅ **AUCUN** (binaire pré-compilé, ~30 s) | notebook `colab_ollama_ministral.ipynb` + `colab_run_ollama.py` | **Le plus rapide à lancer.** Schéma JSON via l'API native Ollama |
>
> Le build llama.cpp complet (kernels `ggml-cuda`, dont des centaines de
> `template-instances/fattn-*`) est très long sur les 2 vCPU de Colab gratuit.
> **Si tu veux éviter ça → variante 🅱️ Ollama.** La section « VARIANTE OLLAMA »
> en bas décrit son fonctionnement. Le reste de ce README couvre la variante 🅐.

L'architecture n'est PAS modifiée. L'orchestrateur sait déjà tourner en
mono-modèle : si on ne fournit que `--model` (= `agentic_model`) sans
`--context-model` ni `--worker-model`, `routing_actif=False` et **toutes les
phases** (extraction, Context Builder, Planner, Designers, Workers/Juges)
utilisent ce même modèle. La seule adaptation Colab est le **lancement GPU de
llama-server**, fait par monkeypatch dans `colab_run.py` (zéro fork des sources).

---

## 1. Runtime Colab

`Exécution > Modifier le type d'exécution > GPU`

| GPU | VRAM | Verdict pour un 14B Q4_K_M (ctx 16k) |
|-----|------|--------------------------------------|
| **T4** (gratuit) | 16 Go | ✅ OK (~12 Go utilisés). Le minimum viable. |
| **L4** (Pro) | 24 Go | ✅ Confortable, autorise Q5/Q6 ou ctx plus grand. |
| **A100** (Pro+) | 40 Go | ✅✅ Le plus rapide, large marge. |

> Le CPU n'est utilisé que pour les embeddings MiniLM (rapide). Tout le LLM
> 14B tourne sur le GPU (`-ngl 99`).

---

## 2. Fichiers à mettre sur Colab

> ⚠️ On n'**uploade pas de dossier** : Colab prend les fichiers **un par un, à
> plat** dans `/content`. Le dossier `_colab_14b/` n'est qu'un rangement sur ton
> PC. Tu ne déposes sur Colab que des fichiers isolés.

Étapes :

1. **Ouvre le notebook** dans Colab : `colab.research.google.com` →
   `Fichier > Importer un notebook` → sélectionne `colab_orchestrator_14b.ipynb`.
2. **Uploade 3 fichiers à plat** (cellule 5 du notebook) :
   - `meeting_minutes_pipeline.py`  (racine du projet)
   - `_bench_orchestrator.py`       (racine du projet)
   - ton transcript normalisé `.txt` (ex. `dicte_audio_3.normalized.txt`)

`colab_run.py` n'a **pas** besoin d'être uploadé : le notebook l'écrit
tout seul (cellule 6, `%%writefile`). Le fichier `colab_run.py` de ce dossier
est juste une **copie de référence** lisible, identique au contenu embarqué.

Le notebook se charge du reste (build llama.cpp CUDA, téléchargement du modèle,
exécution, affichage).

---

## 3. Ordre des cellules du notebook

1. `nvidia-smi` — vérifier le GPU.
2. `pip install` — sentence-transformers, psutil, huggingface_hub (numpy/scipy/torch déjà présents).
3. **Build llama.cpp CUDA** (~6-10 min) — cible `llama-server` uniquement.
4. **Télécharger le modèle 14B** (GGUF Q4_K_M, ~9 Go).
5. **Uploader** les 3 fichiers (les 2 .py + le transcript).
6. **Écrire `colab_run.py`** (automatique, `%%writefile`).
7. **Lancer** (adapter `--participants` et `--transcript`).
8. Afficher le `compte_rendu_v4.md`.
9. Télécharger CR + `orchestrator_v4.json` (trace complète des agents).

### Option « zéro upload » (git clone)
Si tu pousses ton dépôt sur GitHub (`git add -A && git commit && git push`),
tu peux remplacer la cellule 5 par un simple :
```
!git clone https://github.com/belguitarmelissazina/meeting_assistant.git /content/repo
%cp /content/repo/meeting_minutes_pipeline.py /content/repo/_bench_orchestrator.py /content/
```
(et `--transcript` pointant vers ton fichier dans le repo). Attention : pense à
committer la version à jour de `meeting_minutes_pipeline.py`.

---

## 4. Modèle 14B — choix par défaut et alternatives

Par défaut : **Qwen2.5-14B-Instruct** (`bartowski/Qwen2.5-14B-Instruct-GGUF`,
fichier `Qwen2.5-14B-Instruct-Q4_K_M.gguf`). Très bon en français et surtout
fiable sur la **sortie JSON contrainte** (`response_format` json_schema), ce que
chaque agent du pipeline exige.

Alternatives (changer `repo_id` / `filename` en cellule 4, et `--model`) :

| Modèle | repo_id (bartowski) | fichier Q4_K_M | Note |
|--------|---------------------|----------------|------|
| Qwen2.5-14B-Instruct | `bartowski/Qwen2.5-14B-Instruct-GGUF` | `Qwen2.5-14B-Instruct-Q4_K_M.gguf` | **défaut**, JSON solide |
| Phi-4 (14B) | `bartowski/phi-4-GGUF` | `phi-4-Q4_K_M.gguf` | bon raisonnement |
| Qwen2.5-14B-Instruct-1M | `bartowski/Qwen2.5-14B-Instruct-1M-GGUF` | `Qwen2.5-14B-Instruct-1M-Q4_K_M.gguf` | si très longs transcripts |

Quantizations : `Q4_K_M` (~9 Go, défaut équilibré) · `Q5_K_M` (~10.5 Go,
qualité ↑, demande L4/A100) · `Q4_K_S` (~8 Go, si T4 trop juste).

---

## 5. Réglages (`colab_run.py`)

```
--server-bin   chemin du llama-server compilé CUDA
--model        GGUF 14B unique (toutes les phases)
--transcript   transcript normalisé .txt
--participants "Nom Prénom, Autre Nom"   (noms EXACTS = anti-hallucination)
--entreprises  "Société A, Société B"     (optionnel)
--output-dir   dossier de sortie
--ngl          couches offloadées GPU (99 = tout — défaut)
--ctx          taille de contexte (16384 défaut ; 8192 si OOM sur T4)
```

Sorties dans `--output-dir` : `compte_rendu_v4.md` (le CR) +
`orchestrator_v4.json` (trace : contexte, plan, designers, workers, timings) +
`sections.json` (extraction par chunk, réutilisable).

---

## 6. Dépannage

- **OOM CUDA / le serveur crash au démarrage** : baisse `--ctx 8192`, ou prends
  `Q4_K_S`, ou passe en L4/A100. En dernier recours `--ngl 40` (offload partiel,
  plus lent).
- **`--flash-attn on` rejeté** : ton build llama.cpp est ancien ; recompile la
  cellule 3 (master récent). Flash-attn est requis car le KV-cache est quantifié
  (`q8_0`).
- **Temps d'exécution** : le pipeline est **séquentiel** (extraction = 3 appels
  LLM/chunk, puis agents et workers 1 par 1). Sur T4 avec un 14B, compte ~15-40
  min selon la longueur de la réunion. Garde l'onglet actif (Colab coupe les
  sessions inactives).
- **Speaker mapping non appliqué** : normal si la diarisation a fusionné des
  locuteurs (garde-fou G1) — le CR passe en mode prudent sur les noms.
- **Embeddings lents** : MiniLM tourne sur CPU (volontaire, pour laisser tout le
  GPU au 14B) ; c'est rapide même ainsi.

---

# 🅱️ VARIANTE OLLAMA (zéro build)

Pour éviter complètement la compilation de llama.cpp. **Ne modifie aucun de tes
fichiers source.**

Fichiers : notebook **`colab_ollama_ministral.ipynb`** + runner
**`colab_run_ollama.py`** (le notebook l'écrit lui-même, rien à uploader pour lui).

### Principe
- Ollama est **le moteur llama.cpp** distribué **pré-compilé avec CUDA**
  (`curl -fsSL https://ollama.com/install.sh | sh`, ~30 s) → perfs GPU
  identiques, sans build.
- `colab_run_ollama.py` monkeypatch deux choses (sans toucher tes sources) :
  - `start_llm_server_slots` → no-op + health-check (Ollama tourne déjà).
  - `llm_complete` → appelle l'API **native** Ollama `/api/chat` avec
    `format=<json_schema>`. ⚠️ Indispensable : l'endpoint *OpenAI* d'Ollama
    (`/v1/chat/completions`) **ignore** `response_format: json_schema`
    (issue ollama#10001), alors que `format` sur `/api/chat` applique bien une
    grammaire dérivée du schéma → même rigueur JSON que llama.cpp natif.
- `context_model`/`worker_model` = None ⇒ **un seul modèle pour toutes les phases**.

### Étapes (notebook `colab_ollama_ministral.ipynb`)
1. `nvidia-smi`
2. `pip install sentence-transformers psutil huggingface_hub`
3. **Installer Ollama** (`curl ... | sh`, ~30 s)
4. **Télécharger le GGUF + `ollama serve` (arrière-plan) + `ollama create ministral`**
5. **Uploader** les 3 fichiers (`meeting_minutes_pipeline.py`, `_bench_orchestrator.py`, transcript)
6. **Écrire `colab_run_ollama.py`** (auto, `%%writefile`)
7. **Lancer** (adapter `--participants` / `--transcript`)
8. Afficher / 9. Télécharger

### Changer de modèle
Le notebook utilise **Ministral-3-8B** (`lmstudio-community/Ministral-3-8B-Instruct-2512-GGUF`,
fichier `Ministral-3-8B-Instruct-2512-Q4_K_M.gguf`). Pour un autre modèle :
change `repo_id`/`filename` à la cellule 4, garde le nom Ollama `ministral`
(ou change-le partout, y compris `--model-name`).

### Dépannage Ollama
- **`ollama: command not found`** → relance la cellule 3 (install).
- **`Modele Ollama 'ministral' introuvable`** → relance la cellule 4 (`ollama create`).
- **Ollama tourne sur CPU au lieu du GPU** → vérifie le runtime GPU (cellule 1) ;
  Ollama détecte CUDA automatiquement, sinon regarde `/content/ollama.log`.
- **Sortie JSON non conforme / fallbacks** → vérifie que ta version d'Ollama est
  récente (l'install script prend la dernière) ; `format=<schema>` requiert v0.5+.
