# Compte rendu benchmark — Génération de comptes rendus de réunion par LLM locaux

> Document de synthèse de toutes les expériences menées sur la chaîne « transcript → compte rendu » exécutée 100 % en local sur CPU (8–16 Go RAM) avec `llama-server` (llama.cpp).
> Périmètre : 4 générations d'architectures (v1 → v4) + 4 architectures alternatives (`pipeline.py`, `pipeline_3calls`, `pipeline_hybrid`, `pipeline_nuextract`), 7 modèles GGUF testés, 3 transcripts source.

---

## 1. Vue d'ensemble

### 1.1 Objectif

Produire automatiquement un **compte rendu de réunion structuré en Markdown** (Executive Summary, Sujets abordés, Décisions, Actions, Recommandations) à partir d'un transcript brut issu de la diarisation Sherpa + Kroko. Le tout :

- **100 % local** (pas d'envoi de données client à OpenAI/Anthropic),
- **CPU uniquement** (la cible métier est un poste de travail consultant 8–16 Go RAM, pas de GPU),
- **Sans halluciner** (un consultant doit pouvoir signer le rendu : pas d'invention, pas de développement de sigle au hasard).

### 1.2 Stack technique commune

| Couche | Choix | Pourquoi |
|---|---|---|
| Runtime LLM | `llama-server.exe` (llama.cpp) | API OpenAI-compatible, mmap GGUF, KV cache quantifié, gestion des slots `--parallel N` |
| Format poids | GGUF Q4_K_M / Q4_0 / Q6_K | Quantification 4 bits = ~1.5–2.5 Go par modèle 3B, tient en RAM CPU |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (CPU) | 384-d, multilingue acceptable, < 100 Mo, batch 32 |
| Tracking | MLflow (sqlite + artifacts) | Comparaison des runs, paramètres, prompts, courbes |
| Évaluation | BERTScore (fr) + LLM-as-judge optionnel + scorers rule-based | Fidélité vs hallucination |

### 1.3 Modèles évalués

| Slug | Fichier GGUF | Taille | Quantif | Famille |
|---|---|---:|---|---|
| **ministral** | `mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf` | ~1.9 Go | Q4_K_M | Mistral 3B |
| **mistral7b** | `Mistral-7B-Instruct-v0.3-Q4_K_M.gguf` | ~4.1 Go | Q4_K_M | Mistral 7B |
| **qwen2.5** | `qwen2.5-3b-instruct-q4_0.gguf` | ~1.9 Go | Q4_0 | Qwen 2.5 3B |
| **qwen3** | `Qwen_Qwen3-4B-Q4_K_M.gguf` | ~2.5 Go | Q4_K_M | Qwen 3 4B (thinking) |
| **smollm3** | `HuggingFaceTB_SmolLM3-3B-Q4_K_M.gguf` | ~1.9 Go | Q4_K_M | HF SmolLM3 |
| **lfm2-thinking** | `LFM2.5-1.2B-Thinking-Q4_0.gguf` | ~660 Mo | Q4_0 | Liquid LFM2.5 |
| **lfm2-extract** | `LFM2-1.2B-Extract-Q4_K_M.gguf` | ~750 Mo | Q4_K_M | Liquid Extract |
| **lfm2-transcript** | `LFM2-2.6B-Transcript-Q6_K.gguf` | ~2.0 Go | Q6_K | Liquid Transcript |
| **nuextract** | `NuExtract-2.0-2B-Q4_K_M.gguf` | ~1.3 Go | Q4_K_M | Extraction structurée |

### 1.4 Sources de transcript utilisées

| Source | Segments | Origine |
|---|---:|---|
| `transcript1.txt` | 556 | Sortie brute Sherpa diarisation + ASR Kroko |
| `transcript_formatted.txt` | 247 | Re-segmentation par locuteur (lignes fusionnées) |
| `dicte_audio_3.normalized.txt` | 266 | Transcript normalisé (post `normalize_transcript.py`) |

> Les trois sources couvrent **la même réunion** (~1h30, ~9 participants, échange exploratoire IA générative entre RTE / IL Consulting / IEB / IELTS sur les cas d'usage MCP, NLP, génération de rapports). C'est volontaire : ça permet de comparer pipelines et modèles **sur la même matière**.

---

## 2. Architectures pipeline — principe et évolution

Quatre générations principales se sont succédé. Chacune corrige un défaut identifié dans la précédente.

### 2.1 V1 — Sliding Windows + HDBSCAN + LLM par cluster

**Fichier :** `meeting_minutes_pipeline.py`

```
Transcript → Sliding windows → Embeddings → HDBSCAN → LLM/cluster → LLM final
```

**Principe :**

1. Découpage en fenêtres glissantes (`window_size=4`, `overlap=2`) — chaque fenêtre = 4 segments concaténés au format `[Speaker X]: ...`.
2. Embedding `MiniLM-L6` normalisé (vecteurs L2 unitaires → produit scalaire = cosine).
3. Clustering **HDBSCAN** (`min_cluster_size=3`, `min_samples=2`, métrique euclidienne sur vecteurs normalisés). EOM (Excess of Mass) pour la sélection des clusters.
4. Pour chaque cluster, on rassemble les fenêtres dans l'ordre chronologique et on appelle le LLM (1 prompt = 1 section).
5. Appel final unique pour assembler les sections en compte rendu structuré.

**Défauts identifiés :**

- **Non-monotone temporellement** : un même sujet peut revenir 20 minutes plus tard, HDBSCAN les regroupe → la fenêtre temporelle d'un cluster s'étale → le résumé devient hors-contexte.
- **Cluster -1 (bruit)** : 30–40 % des fenêtres sont jetées comme bruit par HDBSCAN.
- **Micro-clusters** : `min_cluster_size=3` produit beaucoup de petits clusters qui parasitent le LLM final (le contexte d'assemblage explose).

### 2.2 V2 — V1 + post-clustering (fusion + réassignation bruit) + speaker resolution

**Fichier :** `meeting_minutes_pipeline_v2.py`

```
Transcript → Sliding windows (8/3) → Embeddings → HDBSCAN(min=5)
        → Fusion clusters proches → Réassign bruit → Split clusters trop gros (KMeans)
        → LLM/cluster → LLM final
```

**Différences clés vs V1 :**

| Aspect | V1 | V2 |
|---|---|---|
| `window_size / overlap` | 4 / 2 | **8 / 3** (fenêtres plus larges → embeddings plus thématiques) |
| `min_cluster_size` | 3 | **5** (moins de micro-clusters) |
| Post-traitement | aucun | **fusion** (centroïdes cosine ≥ 0.95) + **réassignation bruit** (cosine ≥ 0.30) + **split** par KMeans si > 12 000 chars |
| Speakers | bruts (`SPEAKER_00`) | regex de présentation (« moi c'est X », « je suis Y ») |
| Prompts | basiques | durcis anti-hallucination |
| Assemblage final | LLM bref | LLM structuré (Exec Summary, Participants, Décisions, Actions, Points d'attention) |

**Maths derrière la fusion :** itérativement, on calcule pour toute paire (a, b) de clusters le cosine de leurs centroïdes normalisés :

$$\text{sim}(c_a, c_b) = \frac{\bar{e}_a}{\lVert\bar{e}_a\rVert} \cdot \frac{\bar{e}_b}{\lVert\bar{e}_b\rVert}$$

Si `sim ≥ 0.95`, on fusionne. La boucle s'arrête quand plus aucune paire ne dépasse le seuil.

**Défaut résiduel :** HDBSCAN reste **non-monotone**. Le pipeline n'a aucune garantie que les chunks soient chronologiques. Pour une réunion linéaire (présentations puis discussion sujet par sujet), c'est sous-optimal.

### 2.3 V3 — Topic Boundary Detection (rupture d'algorithme)

**Fichier :** `meeting_minutes_boundary_v3.py`

```
Transcript → Fenêtres glissantes (slide=1) → Embeddings → Sim cosine consécutive
        → Lissage gaussien → Détection de vallées → Chunks chronologiques
        → LLM par chunk → LLM final
```

**Principe :** on **abandonne le clustering** au profit d'une détection de **frontières temporelles** (segmentation linéaire).

1. Fenêtres glissantes de 3 segments avec **slide = 1** (overlap maximal). Pour chaque fenêtre i, on a un embedding `e_i`.
2. Pour chaque paire consécutive, on calcule la similarité cosine :
   $$s_i = e_i \cdot e_{i+1}$$
3. Lissage **gaussien** 1D, `σ = 2.0` :
   $$\tilde{s}_i = \sum_k g_\sigma(k) \cdot s_{i+k}$$
   pour atténuer les variations locales (changement de locuteur, hésitation) et garder seulement les vraies ruptures sémantiques.
4. **Seuil** = 5e percentile des similarités lissées. Toute fenêtre dont `s̃ < seuil` est candidate à une frontière.
5. **Distance min entre frontières** = 8 fenêtres (évite des coupes consécutives sur la même chute).
6. Construction des chunks entre deux frontières. Si un chunk dépasse `max_chunk_chars=30 000`, on le **re-split sémantiquement** (ré-embedding du sous-chunk + frontière à la vallée la plus profonde, récursivement). Pas de découpe mécanique au milieu d'une phrase.

**Avantages :**

- Chronologique par construction → un sujet de 15 min reste un seul chunk.
- Pas de bruit jeté.
- Plus prédictible (les paramètres `sigma`, `percentile`, `min_distance` ont un effet géométrique direct sur le nombre de chunks).
- La courbe de similarité est sauvegardée en PNG pour debug visuel.

**Visualisation typique** (transcript1.txt, 556 segments → 7 frontières → 9 chunks) :

![Courbe de similarité v3 - baseline](compte_rendu_reference.similarity.png)

> Lecture : courbe bleue claire = similarité brute, courbe orange = lissée, lignes rouges verticales = frontières détectées, ligne rouge horizontale pointillée = seuil (percentile 25).

### 2.4 V4 — V3 + assemblage déterministe + 2 appels par chunk + recommandations

**Fichier :** `meeting_minutes_boundary_v4.py`

```
Transcript → V3 (chunking inchangé)
        → [par chunk] LLM #1 résumé JSON + LLM #2 extraction JSON
        → Assemblage Python pur (pas de LLM)
        → LLM Executive Summary (intro transcript + titres/résumés)
        → LLM Recommandations consultant
        → MD final
```

**Changements structurels :**

1. **Séparation résumé / extraction** — au lieu d'un seul prompt « fais-moi tout », on coupe en deux :
   - **Appel #1** (`PROMPT_RESUME`) : titre + résumé narratif, 3-4 phrases. Schéma JSON `{titre, resume}`.
   - **Appel #2** (`PROMPT_EXTRACTION`) : extraction pure des décisions et actions, avec **few-shot négatifs** (« j'ai développé X » → tableau vide ; « on pourrait faire Y » → tableau vide). Schéma JSON `{decisions, actions[]}`.

   *Pourquoi :* les modèles 3B mélangent les genres si on demande tout d'un coup (un résumé devient une liste de décisions). Séparer = chaque appel a un seul rôle, le prompt tient.

2. **Sortie JSON contrainte** par `response_format: json_schema` (supporté par llama.cpp via grammaires GBNF dérivées du schéma). Plus de fallback regex si le modèle hallucine du Markdown.

3. **Assemblage Python déterministe** (`assemble_report`) — pas d'appel LLM pour fabriquer le Markdown final. On boucle sur les sections, on génère les tables Décisions et Actions, on dédupliquera **rien** (chronologique, transparent).

   *Pourquoi :* l'appel LLM final v3 réécrivait souvent les sections, perdait des actions, ou en inventait de nouvelles à l'assemblage. En remplaçant par du Python pur, on gagne en fidélité **et** on économise un appel coûteux (~10 min sur Ministral).

4. **Executive Summary** = 1 petit appel LLM avec **(intro transcript + titres/résumés)** seulement. Le contexte injecté est minuscule (~1500 tokens) → rapide.

5. **Speaker mapping** optionnel via LLM : si l'utilisateur fournit `--participants "Jérôme M., Maya S., …"`, un appel LLM analyse les 80 premières lignes du transcript et construit le mapping `SPEAKER_XX → Nom (Entreprise)`.

6. **Recommandations consultant** — un appel LLM final sur les sections agrégées (titres + résumés + décisions + actions) qui génère 3 à 7 recommandations actionnables, taggées « court terme / moyen terme ». **Explicitement marquées comme générées par IA**, séparées des faits de la réunion.

#### 2.4.1 Gestion technique de `llama-server` en V4

**Démarrage** (`start_llm_server_slots`) :

```bash
llama-server.exe -m <gguf>
                 --port 8765
                 --ctx-size N*ctx_base       # ctx-size total = nb_slots * ctx_base
                 --parallel N                  # N requêtes simultanées
                 --fit off
                 --log-disable
                 [--threads 6]
                 [-ngl 0]                       # CPU pur
```

- `--parallel N` active **N slots indépendants** côté serveur. Chaque slot a son propre KV cache.
- `--ctx-size` est le **contexte total** (le serveur le divise en N parts égales). Cohérent avec les chunks de ~30 k chars (~7 500 tokens).
- `--fit off` empêche llama-server de tronquer silencieusement le prompt s'il dépasse le ctx du slot — on préfère échouer bruyamment.

**Échantillonneur RAM** (`RamSampler`) — un thread daemon Python qui appelle `psutil` toutes les 0.5 s sur le PID `llama-server` (et ses enfants) pendant les appels LLM, pour mesurer **pic / moyenne** de RAM serveur. C'est ce qui alimente les colonnes `ram_llama_server_peak_mb` des métriques.

**Parallélisme côté Python** :

- Mode `--parallel-chunks 1` (séquentiel) : `for chunk in chunks: generate_section_json(chunk)`.
- Mode `--parallel-chunks N` : `ThreadPoolExecutor(max_workers=N).map(...)`. Comme l'appel HTTP est I/O-bound (le travail est dans `llama-server`), Python n'est pas pénalisé par le GIL.
- Mode `--parallel-chunks auto` : `N = len(chunks)` — un slot par chunk. Tient si la RAM le permet (chaque slot ajoute ~ctx_base × KV/token).

**Pourquoi pas asyncio ?** Les appels sont longs (10–60 s/chunk en CPU), pas nombreux (10–15). `ThreadPoolExecutor` suffit largement et reste lisible. Asyncio aurait fait sens si on avait des milliers d'appels courts.

#### 2.4.2 KV cache et JSON-schema côté llama.cpp

- `llm_kv_cache_type = "q8_0"` est exposé en config v3/v2 (mais l'option n'est pas passée dans la commande actuelle — TODO si on veut grappiller ~30 % de RAM sur le contexte).
- `response_format = {"type": "json_schema", "json_schema": {...}}` est intercepté par llama.cpp qui compile le schéma en grammaire GBNF et **contraint la génération token par token**. Le modèle ne peut littéralement pas produire un caractère qui violerait le schéma. C'est ce qui rend la pipeline V4 robuste face à un Ministral 3B qui sinon échappe régulièrement le JSON.

### 2.5 Architectures alternatives (« tracks parallèles »)

| Pipeline | Idée centrale | Verdict |
|---|---|---|
| `pipeline.py` (multi-pass v1) | 4 extractions par chunk (speakers / topics / decisions / details) puis fusion Python puis 3 sections LLM | Solide mais 40 appels LLM = lent (Mistral 7B : 6363 s ≈ 1h46) |
| `pipeline_3calls.py` | 1 appel LFM-Extract sur tout le transcript + 1 résumé exécutif + 1 rapport détaillé (KV cache hit) | Rapide (~370 s) mais coupe court : zéro chunking, dépend du ctx 32k |
| `pipeline_hybrid.py` | LFM-Extract (par chunk) + Python (fusion) + LFM-Transcript ×2 (rapport) | Compromis intéressant ; abandonné quand V4 a montré meilleur tradeoff |
| `pipeline_nuextract.py` | NuExtract 2B en mode `verbatim-string` (extraction littérale, T=0) puis Qwen 2.5 pour rédaction | Excellente fidélité d'extraction (par construction) mais Qwen3B en rédaction reste générique |

---

## 3. Résultats — métriques quantitatives

### 3.1 Source `transcript1.txt` (556 segments) — comparaison architectures × modèles

| Pipeline | Modèle | Durée | RAM serveur | n_chunks/clusters | Décisions | Actions | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| V2 (HDBSCAN) | Ministral 3B | **39:22** | 3 786 Mo | 5 clusters | — | — | Beaucoup de bruit, prompt durci |
| V2 (HDBSCAN) | Qwen 2.5 3B | **20:48** | 2 670 Mo | 5 clusters | — | — | Plus rapide, narratif générique |
| V2 (HDBSCAN) | Qwen3 4B | **48:55** | 4 670 Mo | 5 clusters | — | — | Mode thinking → ralentit fortement |
| V2 (HDBSCAN) | SmolLM3 3B | **24:48** | 3 870 Mo | 5 clusters | — | — | Acceptable mais titres pauvres |
| **V3 (Boundary)** | Ministral 3B | **26:37** | 4 389 Mo | 9 chunks | — | — | -32 % vs V2 sur même modèle |
| **V3 (Boundary)** | Qwen 2.5 3B | **12:13** | 5 039 Mo | 9 chunks | — | — | Plus rapide, sections courtes |
| **V3 (Boundary)** | Qwen3 4B | **32:40** | 4 191 Mo | 9 chunks | — | — | Thinking encore lent |
| **V3 (Boundary)** | SmolLM3 3B | **14:56** | 4 375 Mo | 9 chunks | — | — | OK, narratif moyen |
| **V3 (Boundary)** | Ministral 3B (transcript_formatted) | **27:05** | 2 509 Mo | 6 chunks | — | — | Source plus dense → moins de chunks |

> Légende : `n_chunks` v3/v4 vs `n_clusters` v2. Les colonnes Décisions/Actions n'étaient pas mesurées en v2/v3 (c'est une métrique introduite en v4).

### 3.2 Source `dicte_audio_3.normalized.txt` (266 segments) — comparaison V3 vs V4

| Pipeline | Modèle | Durée | RAM peak | n_chunks | Décisions | Actions | n_LLM_calls |
|---|---|---:|---:|---:|---:|---:|---:|
| V3 (Boundary) | Ministral 3B | **29:15** | 2 945 Mo | 11 | — | — | 11 + 1 = 12 |
| **V4 (Boundary + assemblage déterministe)** | Ministral 3B | **51:52** | 5 825 Mo | 11 | **0** | **0** | 12 |
| **V4 (Boundary + assemblage déterministe)** | Qwen 2.5 3B | **16:10** | 4 165 Mo | 11 | **5** | **9** | 12 |

**Lecture importante :**

- Sur **Qwen 2.5**, V4 = 16 min vs V3 ≈ 29 min sur Ministral : pipeline plus rapide **et** extraction des décisions/actions enfin remplie.
- Sur **Ministral**, V4 a **0 décisions et 0 actions** → le modèle a respecté trop strictement les few-shot négatifs et a tout filtré. C'est la **contrepartie** d'un prompt très conservateur. Qwen 2.5, plus laxiste, en remonte 5/9 — mais avec parfois du bruit (cf. §5 qualité).
- L'écart de durée (52 min vs 16 min) entre Ministral et Qwen 2.5 s'explique par un throughput tokens/s très différent en CPU pur (Ministral plus lent côté llama.cpp pour cette quantif Q4_K_M).

### 3.3 Détail des temps par étape — V4 sur `dicte_audio_3.normalized` (Qwen 2.5)

| Étape | Temps (s) | % du total | Mécanisme |
|---|---:|---:|---|
| chargement | 0.0 | 0.0 % | parsing texte |
| fenêtres glissantes | 0.0 | 0.0 % | slicing segments |
| **embeddings** | **7.3** | 0.8 % | MiniLM-L6 batch 32 CPU |
| détection frontières | 0.0 | 0.0 % | numpy + scipy.ndimage |
| construction chunks | 9.4 | 1.0 % | inclut le re-split sémantique éventuel |
| **génération sections (LLM × 11 chunks)** | **839.8** | **86.5 %** | 2 appels par chunk × 11 = 22 appels LLM |
| **executive summary (LLM ×1)** | **104.4** | **10.8 %** | 1 appel sur intro + résumés |
| assemblage déterministe | 0.001 | 0 % | Python pur |
| **TOTAL** | **970.4** | 100 % | |

### 3.4 Détail des temps par étape — V4 sur `dicte_audio_3.normalized` (Ministral)

| Étape | Temps (s) | % du total |
|---|---:|---:|
| embeddings | 15.1 | 0.5 % |
| construction chunks | 16.1 | 0.5 % |
| génération sections LLM (22 appels) | 2 450.1 | 78.7 % |
| executive summary LLM | 303.6 | 9.8 % |
| **proposals LLM** (recommandations consultant) | 310.6 | 10.0 % |
| assemblage déterministe | 0.001 | 0 % |
| **TOTAL** | **3 112.2** | 100 % |

> ~80 % du temps est dans la génération des sections. C'est le bon levier d'optimisation : passer en `--parallel-chunks 4` divise potentiellement ce poste par 3 (limité par la mémoire et le throughput CPU).

### 3.5 Architectures alternatives (`results/*_metrics.json` à plat)

| Run | Modèle | Durée | Notes |
|---|---|---:|---|
| Multi-pass V1 | Mistral 7B Q4_K_M | **1h46 (6 364 s)** | 40 extractions + 3 générations |
| Multi-pass V1 | Qwen 2.5 3B Q4_0 | **43:38 (2 618 s)** | 40 + 3 |
| Multi-pass V1 | LFM2.5-1.2B-Thinking | 18:14 (1 094 s) | rapide mais rapport vide (295 chars) |
| `pipeline_3calls` | LFM Extract + Transcript | **6:10 (370 s)** | record vitesse mais zéro chunking |
| `LFM2-2.6B-Transcript` (one-shot) | LFM2.6B | 29:09 (1 749 s) | génération décomposée 6 sections |
| Bench LFM2.5-1.2B-Thinking (one-shot) | LFM2.5 | 4:17 (257 s) | 4.37 tok/s, rapport 1 509 chars |

---

## 4. Comparaison vs baseline (référence)

La **baseline** = `compte_rendu_reference.md` produit par V3 + Qwen 2.5, exécuté en 188 s (3:09) sur `transcript1.txt` (cache `.sections.json` activé → seul l'assemblage final a été chronométré). C'est notre point d'ancrage qualitatif (pas le « gold standard » humain — ça n'existe pas dans le projet — mais le rendu jugé acceptable et utilisé pour BERTScore).

| Run | Pipeline / Modèle | Source | Durée | Quel gain vs baseline ? |
|---|---|---|---:|---|
| Référence | V3 / Qwen 2.5 (cache) | transcript1 | 3:09 | — |
| V3 / Qwen 2.5 (cold) | V3 / Qwen 2.5 | transcript1 | 12:13 | « Coût » réel d'une exécution sans cache |
| V4 / Qwen 2.5 | V4 / Qwen 2.5 | dicte_normalized | 16:10 | + tableau Décisions/Actions structuré |
| V4 / Ministral | V4 / Ministral | dicte_normalized | 51:52 | Narratif plus riche, Décisions/Actions trop strictes |

### 4.1 Distribution des chunks et cohérence avec la baseline

Sur `transcript1.txt` la détection de frontières V3 produit **systématiquement 9 chunks** (paramètres figés `window_size=3`, `sigma=2.0`, `percentile=5`, `min_distance=8`). Les frontières tombent aux ruptures naturelles de la réunion :

1. fin du tour de table
2. transition vers présentation IELTS / RTE
3. méthodologie de rédaction
4. agents spécialisés / souveraineté
5. exploration état de l'art / détection de fraude
6. fine-tuning Qwen VL
7. intégration MCP / orchestration

Les courbes `compte_rendu_reference.similarity.png` et `results/meeting_minutes_v4/.../compte_rendu.similarity.png` montrent bien les vallées profondes (sim < 0.65 lissée) à ces transitions, alors que les zones plates (sim ~0.85) correspondent à un même intervenant qui développe.

---

## 5. Comparaison qualitative des rendus

### 5.1 Pourquoi avoir gardé Ministral (et pourquoi Mistral plus généralement)

**Ministral 3B** est conservé dans la suite de modèles malgré sa lenteur parce qu'il **gagne sur le narratif** :

#### Exemple — Section « Présentation des compétences IELTS » (`dicte_audio_3.normalized`)

**Ministral V4 (extrait) :**
> *« SPEAKER_01 a présenté les projets d'intelligence artificielle générative menés chez Ely, en se concentrant sur ses expériences passées et celles depuis son arrivée. Il a détaillé une approche globale visant à transformer des contenus complexes (documents hétérogènes) en formats actionnables, comme des fiches synthétiques ou extraits pertinents pour faciliter les décisions. Ses compétences incluent notamment la gestion de modèles multimodaux, l'industrialisation avec des outils de prétraitement et de monitoring, ainsi que le déploiement localisé de modèles finetunés (ex : QNTubine). Il a aussi évoqué l'utilisation de plateformes comme Mistral et des techniques comme le RAG (Retrieval-Augmented Generation), la vectorisation et l'orchestration. »*

**Qwen 2.5 V4 (même section) :**
> *« SPEAKER_01 a présenté ses compétences en matière d'industrielsisation de contenus complexes, notamment la transformation en multimodalité pour faciliter la prise de décision. Il a également mentionné son travail sur l'industrialisation des modèles hébergés localement et leur fine-tuning, ainsi que l'utilisation de méthodes comme QNTubinefiel et le rag (ranking). Il a également évoqué ses expériences en matière d'orchestration et de déploiement de modèles. »*

**Différences observables :**

| Critère | Ministral | Qwen 2.5 |
|---|---|---|
| Longueur résumé | ~120 mots, 4-5 phrases | ~60 mots, 3 phrases |
| Néologismes / fautes | Rares (« QNTubine » = ré-écoute audio approximative) | Plusieurs (« industrielsisation », « QNTubinefiel », « rag (ranking) ») |
| Développement de sigle | RAG développé correctement (Retrieval-Augmented Generation) | RAG développé incorrectement (ranking) |
| Style | Fluide, francisé | Hâché, anglicismes |
| Citations participants | Cite les noms réels quand présents | Reste sur SPEAKER_XX |

#### Verdict

- **Ministral** : meilleur pour le **rendu lecteur final**. À garder pour les comptes rendus livrés au client (qualité narrative > vitesse).
- **Qwen 2.5** : meilleur pour le **pipeline rapide / debug**. Tolère bien le JSON contraint, extrait correctement les Décisions/Actions, mais le narratif est sec et fait trop d'erreurs sur les noms propres / sigles.

C'est exactement ce différentiel qui justifie le **double track** dans `results/meeting_minutes_v4/dicte_audio_3.normalized/{ministral, qwen2.5}/` : on conserve les deux pour comparaison.

### 5.2 Décisions / Actions — comportement opposé

| Modèle | Décisions extraites | Actions extraites | Interprétation |
|---|---:|---:|---|
| Ministral V4 | **0** | **0** | Filtre trop agressif les « peut-être », « on pourrait » → vide alors qu'il y avait au moins 2 actions réelles (« revenir vers vous », « organiser un atelier design ») |
| Qwen 2.5 V4 | **5** | **9** | Capture les actions mais en sur-extrait certaines (« Définir la structure préétablie » est en réalité du discours descriptif, pas une action future) |

Les **few-shot négatifs** du `PROMPT_EXTRACTION` v4 (« j'ai développé X » → vide ; « on pourrait Y » → vide) marchent bien sur Ministral mais déclenchent un sur-filtrage. Levier futur : ajuster les exemples pour que Ministral reconnaisse au moins les engagements explicites (« je reviens vers vous »).

### 5.3 Executive Summary — Qwen 2.5 vs Ministral

**Ministral V4 (Exec Summary, 9 lignes) :**
> *« Cette réunion vise à établir une collaboration structurée autour des enjeux liés à l'intelligence artificielle générative et ses applications opérationnelles au sein de RTE. Les participants, experts en Data & IA (comme Nordine ou Maya) ainsi que spécialistes des systèmes interactifs pour les opérateurs (Bruno Mélière, Dinka), explorent d'abord un besoin flou de prise de contact pour mieux identifier leurs attentes et compétences communes, sans encore définir de mission précise. […] »*

**Qwen 2.5 V4 (Exec Summary) :**
> *« Le groupe discute autour de la feuille de route Smart Cockpit, mettant en avant l'intérêt des assistants opérateurs avec IA générative. Ils abordent les briques de calcul et études, ainsi que les compétences d'industrielsisation de contenus complexes. SPEAKER_01 propose automatiquement la création et rédaction des rapports EOD rentabilité […] »*

Ministral garde une **vue d'ensemble** (pourquoi la réunion, qui, quoi en commun, où ça va), Qwen 2.5 enchaîne les sujets sans synthèse. C'est exactement ce que l'instruction « ne résume PAS chaque section une par une » du `PROMPT_EXEC_SUMMARY` cherche à éviter — Ministral l'applique mieux.

### 5.4 Hallucinations observées

| Type | Modèle | Exemple | Risque |
|---|---|---|---|
| Sigle inventé | Qwen 2.5 V3 | « MCP (Multi-Channel Platform) » | Faux. Le transcript ne définit jamais MCP. |
| Sigle francisé erroné | Ministral V4 | « MCP (Management of Complex Projects) » | Aussi faux, autre interprétation hasardeuse. |
| Nom déformé | Ministral V4 | « Nordine » au lieu de « Mathieu » | Erreur transcription en amont (Sherpa) propagée |
| Nom déformé | Ministral V4 | « QNTubine » au lieu de « Qwen 2.5 VL » | ASR + LLM ne reconnait pas le modèle |
| Décision inventée | Qwen 2.5 V4 | « Définition d'une structure préétablie pour le rapport » est listé comme décision alors que c'est une description du processus | Sur-extraction |

**Le système-prompt v3 contient explicitement** :
> *« N'invente JAMAIS le développement d'un sigle ou acronyme si tu ne le connais pas. »*

Malgré ça, les modèles 3B contournent régulièrement la consigne quand le sigle est répété ≥5 fois dans le chunk. **C'est un défaut intrinsèque de la classe 3B Q4** ; un modèle 7B (Mistral 7B Q4_K_M) tient mieux mais coûte 1h46 par run (cf. multi-pass v1).

---

## 6. Comparaison V3 vs V4 sur le même rendu

Ministral, source `transcript_formatted.txt`, V3 :
- 6 chunks → 9 sections finales (le LLM final V3 sub-divise)
- Tableau Décisions/Actions reconstruit par le LLM final → **risque de réécriture**
- Pas de section « Recommandations consultant »
- Durée : 27:05

V4 sur même source aurait donné :
- 6 chunks → 6 sections (pas de re-split par LLM)
- Tableau Décisions/Actions = **concaténation Python** des sorties JSON par chunk → traçabilité parfaite (chaque ligne = un chunk_id source)
- Section « Recommandations consultant » générée séparément, étiquetée IA
- Durée : ~30 min (un peu plus à cause du double appel par chunk)

**Tradeoff résumé :**

| Critère | V3 | V4 |
|---|---|---|
| Appels LLM | n_chunks + 1 | 2 × n_chunks + 2 (résumé + extraction + exec summary + proposals) |
| Durée (Ministral, ~10 chunks) | ~26 min | ~52 min |
| Fidélité du tableau actions | Moyenne (LLM réécrit) | Élevée (concat Python) |
| Recommandations consultant | Non | Oui |
| Risque inversion sections | Possible (LLM final) | Nul (tri par `_start_time`) |
| Schéma JSON contraint | Non | Oui (`response_format`) |

---

## 7. Synthèse — quoi utiliser, dans quel cas

| Cas | Recommandation |
|---|---|
| **Prod consultant — rendu signé client** | V4 + **Ministral** (lent mais narratif net). Lancer en arrière-plan. |
| **Itération rapide / debug pipeline** | V4 + **Qwen 2.5** (16 min sur 1h30 d'audio). Idéal pour ajuster les prompts. |
| **Speaker mapping requis** | V4 avec `--participants "..."` + `--entreprises "..."` (LLM analyse les 80 premières lignes) |
| **Recommandations consultant** | V4 (le seul à les générer ; étiquetées IA, donc auditables) |
| **Audio mal transcrit** | Pré-traiter avec `normalize_transcript.py` puis lancer V4 (cf. `dicte_audio_3.normalized.txt`) |
| **Réunion linéaire (présentations puis Q&A)** | V3/V4 (boundary chronologique) toujours préférable à V2 (clustering) |
| **Réunion polyphonique (saute de sujet en sujet)** | V2 reste théoriquement adapté — mais en pratique V4 reste meilleur grâce au re-split sémantique des gros chunks |
| **Modèle minuscule disponible** | `pipeline_3calls` avec LFM-Extract + LFM-Transcript (370 s) — mais qualité narrative pauvre |

---

## 8. Limites connues et pistes d'amélioration

1. **KV cache quantifié non activé en commande** — `llm_kv_cache_type = "q8_0"` est dans la config v3 mais pas dans `start_llm_server_slots`. À ajouter (`--cache-type-k q8_0 --cache-type-v q8_0`). Gain attendu : ~30 % de RAM serveur sur les longs ctx.

2. **Parallélisme chunks pas encore exploité** — toutes les runs présentées sont en `seq` (1 slot). En `--parallel-chunks 4` sur Qwen 2.5 on devrait passer de 16 min à ~5 min. Limité par la RAM (5 Go × 4 ≠ 16 Go disponibles).

3. **Speaker mapping fragile** — les regex v2 et le LLM v4 échouent quand le tour de table est implicite. `dicte_audio_3.normalized.txt` ne nomme jamais explicitement la moitié des speakers → le mapping reste partiel.

4. **Few-shot extraction trop conservateurs sur Ministral** — explique les `n_actions_total=0`. Solution : ajouter un exemple positif fort (« je reviens vers vous » → action).

5. **Pas de juge LLM exécuté en runs présentés** — `--judge openai:/gpt-4o-mini` est implémenté (`run_llm_judge`) mais nécessite `OPENAI_API_KEY`. À lancer ponctuellement pour valider la fidélité avant un livrable.

6. **BERTScore vs `compte_rendu_reference.md`** — implémenté (`compute_bertscore`) mais nécessite `pip install bert-score` et télécharge ~500 Mo de modèle BERT au premier appel. Idéal pour comparer Ministral V4 à la baseline V3/Qwen.

7. **Hallucinations résiduelles sur les sigles** — peut être adressé par un **post-processing Python** : whitelist des sigles connus du domaine RTE (MCP, EOD, RAG, NLP, POC, VLM, OCR), tout autre sigle inconnu → on remplace son développement par `(développement non précisé)`.

---

## 9. Annexe — schéma résumé des 4 architectures

```
V1  ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌─────────────┐   ┌─────────────┐
    │transcript│ → │ windows  │ → │ embed   │ → │ HDBSCAN     │ → │ LLM/cluster │ → assemblage LLM
    └──────────┘   │ 4 / 2    │   │ MiniLM  │   │ min=3       │   │ (1 prompt)  │
                   └──────────┘   └─────────┘   └─────────────┘   └─────────────┘

V2  identique à V1 + post-clustering :
    HDBSCAN(min=5) → fusion centroïdes(cos≥.95) → réassign bruit(cos≥.30) → split KMeans si > 12k chars
    + speaker resolution regex + prompts durcis + assemblage LLM structuré

V3  ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌──────────────────────┐   ┌────────┐   ┌────────────┐
    │transcript│ → │ windows  │ → │ embed   │ → │ sim cosine + gauss   │ → │ chunks │ → │ LLM/chunk  │ → assemblage LLM
    └──────────┘   │ 3 slide=1│   │ MiniLM  │   │ → vallées (perc 5)   │   │ chrono │   │ (1 prompt) │
                   └──────────┘   └─────────┘   │ + min_dist 8         │   │ + re-  │   └────────────┘
                                                 │ + re-split sémantique│   │ split  │
                                                 └──────────────────────┘   └────────┘

V4  V3 (chunking) + :
    [par chunk]   LLM #1 résumé JSON (titre + résumé)
                  LLM #2 extraction JSON (décisions + actions, few-shot négatifs)
    [global]      LLM #3 Executive Summary (intro + titres/résumés)
                  LLM #4 Recommandations consultant
    [Python]      assemble_report() → Markdown final déterministe
                  speaker_mapping LLM optionnel (--participants)
                  RamSampler (thread psutil 0.5s)
                  llama-server --parallel N --ctx-size N*ctx_base
                  response_format json_schema (GBNF) sur tous les appels LLM #1, #2
```

---

## 10. Annexe — paramètres figés des runs présentés

| Param | Valeur | Effet |
|---|---|---|
| `boundary_window_size` | 3 | Nb segments / fenêtre d'embedding |
| `boundary_smoothing_sigma` | 2.0 | σ du gaussien 1D — plus haut = courbe plus lisse |
| `boundary_percentile` | 5.0 | Seuil = percentile 5 — plus bas = moins de coupes |
| `boundary_min_distance` | 8 | Distance min entre 2 frontières — évite micro-chunks |
| `max_chunk_chars` | 30 000 | Au-delà → re-split sémantique récursif |
| `embedding_model` | `all-MiniLM-L6-v2` | 384-d, CPU, ~22 Mo |
| `embedding_batch_size` | 32 | Batch pour `model.encode` |
| `llm_temperature` | 0.2 | Bas = factuel, haut = créatif (on veut factuel) |
| `llm_repeat_penalty` | 1.1 | Évite que le modèle boucle |
| `llm_n_threads` | 6 | CPU threads pour llama.cpp (n_cores − 2) |
| `llm_n_gpu_layers` | 0 | CPU pur, pas de GPU |
| `llm_n_ctx` | 0 (= 32768 défaut) | Contexte par slot |
| `--parallel` (llama-server) | 1 (mode seq) | Slots simultanés |
| `--fit` | off | Pas de troncature silencieuse |
