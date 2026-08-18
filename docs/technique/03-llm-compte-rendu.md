# Brique 3 — Génération du compte rendu (LLM)

**Fichiers :** [meeting_minutes_pipeline.py](../../meeting_minutes_pipeline.py) (socle + moteur local),
[audio_capture/live_llm.py](../../audio_capture/live_llm.py) (variante temps réel),
[mistral_minutes.py](../../mistral_minutes.py) (moteur API),
[normalize_transcript.py](../../normalize_transcript.py) (prétraitement)
**Rôle :** transformer un transcript attribué par locuteur en compte rendu de
réunion structuré.

> **Périmètre.** Ce document décrit uniquement ce qui est **inclus dans
> l'application**. Le dépôt contient d'autres moteurs en cours de développement
> (orchestrateur agentique, assistant live) qui ne sont pas livrés : ils ne sont
> pas documentés ici. Voir §11.

---

## 1. Les trois chemins

Il y a **un seul format de sortie** — `compte_rendu.md` — produit par trois
chemins différents selon le contexte.

| Chemin | Quand | Moteur | Où |
|---|---|---|---|
| **Live local** | pendant l'enregistrement | Ministral 3B, llama-server local | `live_llm.py` |
| **Batch local** | après coup, mode par défaut | Ministral 3B, llama-server local | `meeting_minutes_pipeline.py` |
| **Batch Mistral** | après coup, si l'utilisateur le choisit | `mistral-large-latest`, API | `mistral_minutes.py` |

**Le point à retenir : les deux chemins locaux partagent le même code.** La
variante live ne réimplémente ni les prompts, ni les appels LLM, ni
l'assemblage — elle appelle `generate_section_json`, `build_exec_summary`,
`build_plan_attack` et `assemble_report` de `meeting_minutes_pipeline`. Seul le
**découpage en chunks** est réécrit, parce qu'il doit fonctionner en flux (§7).

Le moteur Mistral, lui, est complètement indépendant : aucune ligne partagée,
aucun découpage, un seul appel API (§8).

### Qui déclenche quoi

```
ENREGISTREMENT dans l'app
   └─ enableLiveLlm: true  (les 3 points d'entrée l'envoient toujours)
        └─ CR produit AU FIL DE L'EAU, prêt au clic sur Stop
             → job marqué `done`, l'utilisateur n'a rien à lancer

AUDIO UPLOADÉ (ou enregistrement dont le live a échoué)
   └─ l'utilisateur clique « Lancer le traitement »
        └─ sélecteur local / mistral dans le panneau  (défaut : local)
             ├─ backend.exe minutes          → meeting_minutes_pipeline
             └─ backend.exe mistral-minutes  → mistral_minutes
```

Le choix vient de [JobPanel.tsx:366](../../webapp/components/JobPanel.tsx#L366)
et transite par le champ `llm` du corps de `POST /api/jobs/{id}/process`. Le
backend traduit en nom de sous-commande
([main.py:673](../../backend/main.py#L673)).

---

## 2. La chaîne après réunion

```
transcript.txt                       (brique 1 ou 2)
   │
   ├─► backend.exe normalize  ─────► transcript.normalized.txt
   │      découpe chaque tour en phrases, SUPPRIME les timestamps
   │
   └─► backend.exe minutes | mistral-minutes  ─────► compte_rendu.md
          arguments   : --transcript --output [--participants] [--entreprises]
          environnement : MEETING_CONTEXT / MEETING_PARTICIPANTS / MEETING_ENTREPRISES
                          MISTRAL_API_KEY  (mode mistral uniquement)
```

> **Participants et entreprises sont transmis deux fois** — en argument **et**
> en variable d'environnement. Ce n'est pas une redondance : les deux servent à
> des endroits différents du code.
>
> - L'**argument** est lu par le `main()` du moteur et passé explicitement à
>   `resolve_speaker_mapping()`.
> - La **variable d'environnement** est lue bien plus bas, par
>   `_build_system_prompt()` et `_entity_reminder()`, qui construisent les
>   prompts sans avoir accès aux arguments de la ligne de commande.
>
> Le **contexte libre**, lui, ne passe que par l'environnement : aucune fonction
> ne le reçoit en paramètre.

La clé Mistral est injectée depuis les paramètres de l'application uniquement
quand le mode `mistral` est retenu. Le backend vérifie sa présence **avant** de
lancer le sous-processus et fait échouer le job avec un message explicite
([main.py:679](../../backend/main.py#L679)) — le contrôle équivalent dans
`mistral_minutes.py` n'est donc qu'un second filet.

### `normalize_transcript.py`

Une seule chose, mais elle compte : **une ligne = une phrase**.

| Entrée | Sortie |
|---|---|
| `[00:03.20 - 00:11.45]  SPEAKER_00 : bonjour à tous. On commence par le point deux.` | `SPEAKER_00: bonjour à tous.`<br>`SPEAKER_00: On commence par le point deux.` |

Trois détails :

- **Les timestamps sont supprimés** — commentaire du code :
  *« timestamps ignorés pour économiser des tokens LLM »*. Le compte rendu ne
  contient donc aucun horodatage, et le LLM n'a aucune notion de durée.
- Le découpage en phrases protège les abréviations françaises courantes
  (`M.`, `Mme.`, `cf.`, `etc.`, `env.`…) pour ne pas couper dessus.
- Un **découpage dur à 300 caractères** s'applique aux phrases trop longues —
  cas fréquent en ASR, où une absence de ponctuation produit des « phrases » de
  plusieurs lignes.

Cette granularité par phrase est ce qui rend le découpage sémantique
exploitable : les fenêtres d'embedding portent sur 3 phrases, pas sur 3 tours de
parole de longueur arbitraire.

---

## 3. Le socle partagé — `meeting_minutes_pipeline.py`

Ce fichier joue deux rôles : **moteur local après réunion**, et
**bibliothèque** dont la variante live consomme presque tout.

### 3.1 `Config`

Tous les réglages en un dataclass ([l. 89](../../meeting_minutes_pipeline.py#L89)).
Les valeurs qui comptent :

```python
# Découpage sémantique
embedding_model          = "all-MiniLM-L6-v2"
boundary_window_size     = 3        # phrases par fenêtre
boundary_smoothing_sigma = 2.0      # lissage gaussien de la courbe de similarité
boundary_percentile      = 5.0      # seuil : 5 % des similarités les plus basses
boundary_min_distance    = 10       # écart minimal entre deux frontières
max_chunk_chars          = 15000    # au-delà → re-split sémantique récursif

# LLM local
llm_model_path      = models/mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf
llm_n_ctx           = 0             # → 16384 par défaut
llm_n_threads       = 6
llm_n_gpu_layers    = 0             # CPU uniquement
llm_temperature     = 0.2
llm_repeat_penalty  = 1.1
llm_kv_cache_type   = "q8_0"
llm_server_port     = 8765
llm_server_startup_timeout = 86400  # 24 h — autant dire aucun timeout
llm_section_timeout        = 86400

plan_attack_mode = "perchunk"       # surchargeable par MEETING_PLAN_MODE
```

Les deux `86400` ne sont pas un oubli : sur un portable en CPU seul, un chunk
peut prendre plusieurs minutes, et un timeout mal calibré ferait échouer un
traitement qui aurait fini par aboutir. Le parti pris est de **ne jamais
abandonner**.

### 3.2 Le découpage sémantique

C'est ce qui décide du plan du compte rendu : chaque chunk deviendra un
« sujet abordé ».

```
transcript normalisé  (1 phrase par ligne)
   │
   ├─ load_segments_from_transcript()   parse 4 formats de ligne possibles
   │                                     → [{start, end, speaker, text}]
   ├─ build_windows(size=3, slide=1)    fenêtres de 3 phrases consécutives
   │                                     → texte "[speaker]: phrase" concaténé
   ├─ embed_windows()                   MiniLM, vecteurs normalisés L2
   │
   ├─ detect_topic_boundaries()
   │     sim[i] = cos(fenêtre i, fenêtre i+1)
   │     lissage gaussien σ=2
   │     seuil = percentile 5 % des similarités lissées
   │     candidats = points sous le seuil
   │     filtre : au moins 10 fenêtres d'écart entre deux frontières
   │              (à moins de 10, on garde la vallée la plus profonde)
   │
   └─ build_topic_chunks()              coupe aux frontières
         si un chunk > 15 000 chars → _resplit_semantic() récursif :
            re-embedde le chunk, coupe à sa vallée la plus profonde,
            recommence sur chaque moitié tant que c'est trop gros
```

L'intuition : deux passages consécutifs qui parlent du même sujet ont des
embeddings proches. Une **chute** de similarité signale un changement de sujet.
Le lissage évite de réagir aux micro-variations, le seuil au percentile s'adapte
automatiquement à chaque réunion, et la distance minimale empêche de hacher la
réunion en micro-sections.

Le garde-fou des 15 000 caractères est structurel : au-delà, un chunk ne tient
plus dans la fenêtre de contexte du modèle.

### 3.3 Le llama-server

`start_llm_server_slots()` ([l. 550](../../meeting_minutes_pipeline.py#L550))
lance `llama-server.exe` et attend que `/health` réponde.

```
--ctx-size 16384      --parallel N        --flash-attn on
--cache-ram 0         --cache-type-k q8_0 --cache-type-v q8_0
--batch-size 4096     --ubatch-size 1024  --threads 6
--log-disable         (sauf si LLAMA_VERBOSE=1)
```

Le contexte total est **constant** quel que soit `N` : llama.cpp le découpe en
`N` slots de `total/N` tokens. Augmenter le parallélisme ne coûte donc pas de
RAM, tant que chaque chunk tient dans sa part.

> ⚠ **`--cache-ram 0` corrige une fuite mémoire.** La valeur par défaut de
> certaines variantes de llama.cpp est de 8192 Mio de cache de prompt en RAM
> hôte, ce qui **saturait la mémoire après une dizaine de chunks et provoquait
> un arrêt silencieux du processus par Windows**. Le cache de préfixe par slot,
> lui, reste actif — c'est celui qui fait le travail utile, puisque les trois
> appels d'un même chunk partagent le préfixe `[system][chunk]`.

> ⚠ **Le *prompt lookup decoding* a été retiré après mesure**, pas par oubli :
> régression de 5 % sur l'appel de résumé (sortie abstractive courte, taux
> d'acceptation trop bas pour rentabiliser la passe de vérification) et effet
> neutre sur les deux autres. Le commentaire cite le bench de mai 2026.

Le serveur est enregistré via `atexit` pour être tué à la sortie.

### 3.4 Les prompts — les entités figées

Le *system prompt* ([l. 685](../../meeting_minutes_pipeline.py#L685)) est
construit dynamiquement à partir des variables `MEETING_*`. Sa colonne
vertébrale est un ensemble de règles de non-invention :

> Ne mentionne QUE ce qui est EXPLICITEMENT dit — n'invente JAMAIS
> d'informations, décisions, actions, chiffres, dates, échéances — ne développe
> JAMAIS un sigle.

Par-dessus, si l'utilisateur a saisi des participants ou des entreprises, un
bloc **entités figées** est ajouté :

> Les listes ci-dessous sont la vérité. Le transcript contient des erreurs
> phonétiques sur les noms propres : corrige-les silencieusement vers la forme
> EXACTE de la liste. Si un nom ne matche AUCUN élément de la liste, ne le cite
> pas.

C'est la réponse au problème central du couple ASR + LLM : le modèle de
transcription écrit les noms propres phonétiquement, et un LLM à qui l'on ne dit
rien reproduit l'erreur, voire l'aggrave en la « corrigeant » vers un nom
plausible mais faux.

> Ce bloc est répété **deux fois** : dans le *system prompt*, et à nouveau à la
> **fin du prompt utilisateur** via `_entity_reminder()`. C'est un ancrage
> délibéré aux deux extrémités du contexte — les modèles de petite taille
> perdent l'information placée au milieu.

### 3.5 `llm_complete` et le JSON contraint

Tous les appels passent par `llm_complete()`
([l. 726](../../meeting_minutes_pipeline.py#L726)), en HTTP sur l'API compatible
OpenAI de llama-server : `temperature 0.2`, `top_k 50`,
`repeat_penalty 1.1`, plus une liste de séquences d'arrêt.

Le point important : quand un `json_schema` est fourni, il est passé en
`response_format` avec `strict: true`. Le décodage est alors **contraint au
niveau des tokens** — le modèle ne *peut pas* produire du JSON invalide.

C'est ce qui rend le pipeline fiable avec un modèle de 3 milliards de
paramètres : on ne demande pas au modèle de bien se tenir, on l'en empêche
structurellement. Le cap de 2 items par chunk dans le plan d'attaque, par
exemple, est imposé par la grammaire du schéma, pas par une instruction en
français.

### 3.6 `generate_section_json` — le cœur

Pour **chaque chunk**, trois appels LLM en mode `perchunk` (le défaut) :

| # | Appel | Schéma | Produit |
|---|---|---|---|
| 1 | `PROMPT_RESUME` | `SCHEMA_RESUME` | titre, contexte, points-clés |
| 2 | `PROMPT_EXTRACTION` | `SCHEMA_EXTRACTION` | décisions actées |
| 3 | `PROMPT_PLAN_PERCHUNK` | `SCHEMA_PLAN_PERCHUNK` | 0 à 2 items de plan |

Les trois partagent le même préfixe `[system][chunk]` — d'où le gain du cache de
préfixe évoqué en §3.3.

Le troisième appel distingue deux natures d'items :

- **engagement** — quelqu'un s'est explicitement engagé. Responsable et échéance
  sont repris tels quels, avec un filet : un responsable de la forme
  `SPEAKER_07` est remplacé par `—` (le modèle a recopié une étiquette de
  diarisation au lieu d'un nom).
- **suggestion** — recommandation déduite. Responsable et échéance sont
  **forcés** à `—`, pour qu'on ne puisse jamais présenter une recommandation
  comme un engagement pris.

### 3.7 Speaker mapping

`resolve_speaker_mapping()` ([l. 1185](../../meeting_minutes_pipeline.py#L1185))
envoie les **80 premières lignes** du transcript au LLM avec la liste des
participants, et lui demande d'associer `SPEAKER_00` → `{nom, entreprise}`.

Le pari : une réunion professionnelle commence par un tour de table. C'est ce
qui permet de remplacer les étiquettes anonymes par de vrais noms dans tout le
compte rendu.

N'est exécuté **que si** l'utilisateur a saisi des participants.

### 3.8 Assemblage — entièrement déterministe

`assemble_report()` ([l. 1328](../../meeting_minutes_pipeline.py#L1328)) ne fait
**aucun appel LLM**. Il compose le markdown à partir des structures JSON déjà
produites :

```
# Compte rendu de réunion
## 1. Participants        ← seulement si speaker_mapping, groupés par entreprise
## 2. Résumé              ← build_exec_summary (1 appel LLM)
## 3. Sujets abordés      ← une sous-section ### par chunk
## 4. Décisions           ← tableau, agrégation de tous les chunks
## 5. Plan d'attaque      ← tableau, engagements puis suggestions
```

La numérotation est gérée par un compteur qui n'avance que sur les sections
réellement émises : sans participants, « Résumé » devient `1.` et non `2.`.

C'est une décision d'architecture qui mérite d'être soulignée : **la structure
du document ne dépend jamais du LLM.** Le modèle remplit des cases ; le squelette,
les tableaux, la numérotation et l'échappement des pipes markdown sont du code.
Un modèle de 3B ne peut donc pas casser la mise en forme.

Le **plan d'attaque** en mode `perchunk` est lui aussi assemblé sans LLM
([l. 1256](../../meeting_minutes_pipeline.py#L1256)) : les items déjà extraits
par chunk sont concaténés, engagements d'abord, suggestions ensuite. Le mode
`legacy` (un appel LLM final sur les résumés agrégés) reste accessible par
`MEETING_PLAN_MODE=legacy`.

---

## 4. Le moteur local après réunion — `run_pipeline`

[l. 1472](../../meeting_minutes_pipeline.py#L1472) — huit étapes chronométrées
individuellement.

| # | Étape | LLM ? |
|---|---|---|
| 0 | chargement du transcript | — |
| 0b | speaker mapping (si participants) | 1 appel |
| 1 | fenêtres glissantes | — |
| 2 | embeddings MiniLM | — |
| 3 | détection des frontières | — |
| 4 | construction des chunks | — |
| 5 | **génération des sections** | 3 × nb de chunks |
| 6 | executive summary | 1 appel |
| 7 | plan d'attaque | 0 (perchunk) ou 1 (legacy) |
| 8 | assemblage markdown | — |

Total en mode par défaut : **3 × nb_chunks + 1**, plus 1 si speaker mapping.
Une réunion découpée en 8 chunks demande donc ~26 appels au modèle local.

**Ces appels sont séquentiels.** L'option `--parallel-chunks` vaut `1` par
défaut et le backend ne la passe jamais. Même justification que pour le moteur
live (§5.2) : sur CPU, l'inférence est limitée par la bande passante mémoire, et
le bench cité dans l'aide de l'option ne montre aucun gain au-delà d'un slot.
La valeur `auto` (tous les chunks simultanément) existe mais n'est accessible
qu'en ligne de commande.

> ⚠ **Un cache de sections existe et peut surprendre.** L'étape 5 écrit
> `compte_rendu.sections.json` à côté de la sortie, et **le relit s'il existe**
> ([l. 1542](../../meeting_minutes_pipeline.py#L1542)). Relancer un traitement
> sur le même dossier réutilise donc les sections précédentes sans rappeler le
> LLM — pratique pour itérer sur l'assemblage, piégeux si l'on croit tester une
> modification de prompt. Le paramètre `no_cache` existe mais n'est pas exposé
> par le backend.

> ⚠ **Le llama-server est démarré deux fois** quand le speaker mapping tourne :
> une fois avec 1 slot pour le mapping (l. 1495), puis de nouveau avec le nombre
> de slots calculé (l. 1538) — et `start_llm_server_slots` commence par tuer ce
> qui écoute sur le port. On paie donc deux chargements du modèle 3B.

Deux fichiers de debug sont écrits à côté du compte rendu :
`compte_rendu.assembly.json` (comptes de sections, décisions, engagements) et
`compte_rendu.metrics.json` (durées par étape, RAM, nombre d'appels LLM).

---

## 5. Le moteur live — `live_llm.py`

Même destination, contrainte inverse : on ne dispose jamais de la totalité du
texte.

```
mots décodés par l'ASR (brique 2, poll toutes les 2 s)
   │
   ├─ TurnBuilder                 assemble les mots en tours de parole
   ├─ split_turn_sentences(300)   ← même granularité que normalize_transcript
   │
   ├─ StreamingTopicChunker       détection de frontières EN FLUX
   │     └─ à chaque chunk fermé → on_chunk_closed(chunk)
   │
   └─ LiveLLMWorker               pool de slots llama-server
         └─ generate_section_json(chunk)   ← LA MÊME fonction que le batch
              → sections accumulées en mémoire

au clic sur Stop → finalize()
   build_exec_summary + build_plan_attack + assemble_report   ← les mêmes
   → compte_rendu.md
```

Le découpage en phrases à 300 caractères est fait ici en mémoire, par
`split_turn_sentences` — c'est l'équivalent live de `normalize_transcript.py`.

### 5.1 Le chunker en flux — la vraie difficulté

Le batch calcule un seuil **global** (percentile 5 % de toutes les similarités),
ce qui suppose de connaître toute la réunion. En direct, c'est impossible : il
faut décider maintenant, sans savoir ce qui vient.

`StreamingTopicChunker` ([l. 227](../../audio_capture/live_llm.py#L227))
remplace donc le seuil global par trois mécanismes :

| Paramètre | Valeur | Rôle |
|---|---|---|
| `window_size` | 3 | identique au batch |
| `smoothing_sigma` | 2.0 | identique au batch, mais lissage **causal** |
| `rolling_n` | 20 | seuil calculé sur les 20 dernières similarités seulement |
| `k_sigma` | 2.0 | seuil = `moyenne − 2 × écart-type` de cette fenêtre |
| `confirm_delay` | 5 | un creux doit tenir 5 fenêtres avant d'être validé |
| `min_chunk_turns` | 10 | pas de chunk de moins de 10 phrases |
| `max_chunk_chars` | 15000 | identique au batch |

Concrètement ([l. 444](../../audio_capture/live_llm.py#L444)) :

```python
recent    = smoothed[-rolling_n:]          # 20 dernières similarités
threshold = recent.mean() - k_sigma * recent.std()
if smoothed[-1] < threshold:               # → candidat de frontière
```

Le `confirm_delay` est la contrepartie de l'irréversibilité : **un chunk émis
est parti au LLM, on ne peut plus revenir dessus.** Le batch peut réviser ses
frontières autant qu'il veut avant de découper ; le live doit attendre d'être
sûr.

> ⚠ **Aucune frontière ne peut être détectée avant 20 similarités accumulées** —
> `_detect_candidate()` sort immédiatement tant que `n < rolling_n`. À 3 phrases
> par fenêtre, cela représente les ~22 premières phrases de la réunion. Combiné
> au `min_chunk_turns = 10` et au `confirm_delay = 5`, le premier chunk ne peut
> donc pas être fermé tôt : le LLM reste inactif pendant le début de la réunion.

Le garde-fou de taille (`_enforce_size_cap`) traite le cas du sujet unique qui
s'éternise : plutôt que d'attendre `finalize()` — ce qui laisserait le LLM
inactif pendant toute la réunion puis lui donnerait tout d'un coup —, on force
la fermeture. Et on la force **à la vallée sémantique la plus profonde parmi
les candidats en attente**, pas au tour de parole courant : c'est l'équivalent
en flux du `_resplit_semantic` récursif du batch.

### 5.2 Le worker

`LiveLLMWorker` consomme les chunks fermés depuis une file et les soumet à un
`ThreadPoolExecutor` de `parallel_slots` threads (défaut : **1**).

> Le défaut séquentiel est documenté et mesuré : sur CPU, l'inférence est
> limitée par la bande passante mémoire, pas par le nombre de cœurs. Le
> commentaire cite un bench montrant **~0 % de gain** entre `parallel=2` et le
> séquentiel sur Ministral 3B Q4. Un récapitulatif de parallélisme est journalisé
> à la fin pour vérifier ce qui s'est réellement passé.

Les sections peuvent se terminer dans le désordre ; `finalize()` les retrie par
`_start_time` avant l'exec summary et le plan d'attaque, qui attendent un ordre
chronologique.

Le llama-server est arrêté dans un `finally` — quelle que soit l'issue.

### 5.3 Une différence de sortie à connaître

`finalize()` appelle `assemble_report(..., speaker_mapping=None)`
([l. 684](../../audio_capture/live_llm.py#L684)).

> ⚠ **Le compte rendu produit en live n'a jamais de section « Participants ».**
> Le speaker mapping n'est pas exécuté dans ce chemin, alors que le batch le
> fait dès que l'utilisateur a saisi des participants. Les sujets eux-mêmes
> peuvent en outre citer `SPEAKER_?` pour tout ce qui a été traité avant le
> bootstrap de la diarisation (≈ 10 premières minutes, brique 2 §5.4).

---

## 6. Le moteur Mistral — `mistral_minutes.py`

L'exact opposé du moteur local : **un seul appel API, tout le transcript d'un
coup.**

```
transcript.normalized.txt  (intégral)
   └─► POST api.mistral.ai/v1/chat/completions
          model = mistral-large-latest    (surchargeable par MISTRAL_MODEL)
          temperature = 0.2
          timeout = 300 s
       ← markdown complet
   └─► compte_rendu.md
```

Aucun découpage, aucun embedding, aucune dépendance à
`meeting_minutes_pipeline` — le fichier n'importe que la bibliothèque standard.
Le plan du document n'est pas assemblé par du code : il est **dicté au modèle**
dans le prompt utilisateur, section par section, avec les nombres attendus (3 à
8 sujets, 2 à 6 points par sujet, 4 à 10 items de plan, 2 à 4 recommandations).

Les règles de non-invention et le bloc d'entités figées sont repris, dans une
formulation plus développée que la version locale — le budget de contexte n'est
pas un problème ici.

Une particularité qui a demandé un correctif : `_strip_outer_code_fence()`
retire les ` ``` ` que Mistral place fréquemment autour de sa réponse pour
« l'isoler ». Sans ça, tout le compte rendu arrivait dans l'éditeur comme un
unique bloc de code en chasse fixe.

La clé API est lue dans `MISTRAL_API_KEY`, injectée par le backend depuis les
paramètres de l'application. Absente, le processus sort en code 2.

---

## 7. Les trois moteurs en regard

| | Live local | Batch local | Batch Mistral |
|---|---|---|---|
| Modèle | Ministral 3B Q4 | Ministral 3B Q4 | mistral-large-latest |
| Exécution | CPU local | CPU local | API distante |
| Découpage | streaming causal | global, percentile | **aucun** |
| Embeddings | MiniLM | MiniLM | — |
| Appels LLM | 3 / chunk + 1 | 3 / chunk + 1 (+1) | **1** |
| Structure du document | code déterministe | code déterministe | **dictée au modèle** |
| JSON contraint | ✅ | ✅ | ❌ |
| Section Participants | ❌ jamais | ✅ si participants saisis | ✅ via le prompt |
| Connexion requise | non | non | **oui** |
| Latence perçue | ~nulle (déjà prêt) | minutes | ~1 appel |

Les deux colonnes locales partagent tout sauf la première ligne de traitement.
La colonne Mistral ne partage rien.

---

## 8. Fichiers produits

| Fichier | Écrit par | Rôle |
|---|---|---|
| `compte_rendu.md` | les trois moteurs | ✅ le livrable |
| `transcript.normalized.txt` | `normalize` | entrée des moteurs batch |
| `compte_rendu.sections.json` | batch local | **cache** des sections (§4) |
| `compte_rendu.assembly.json` | batch local | debug : comptes de sections, décisions, items |
| `compte_rendu.metrics.json` | batch local | durées par étape, RAM, nombre d'appels |
| `_llama_server_stderr.log` | batch local & live | stderr du llama-server |

---

## 9. Limites connues

### 9.1 Le compte rendu n'a aucune notion du temps

`normalize_transcript` supprime les horodatages pour économiser des tokens.
Aucun moteur ne peut donc situer un sujet dans la réunion, ni indiquer une
durée. Les `start_time` circulent bien dans les structures internes — ils
servent à trier les sections — mais ne parviennent jamais au modèle.

### 9.2 Le cache de sections est invisible

Voir §4. Une modification de prompt sans suppression de
`compte_rendu.sections.json` n'a aucun effet, silencieusement.

### 9.3 Double démarrage du llama-server

Voir §4. Deux chargements du modèle 3B quand le speaker mapping est actif.

### 9.4 Le live ne nomme pas les participants

Voir §5.3.

### 9.5 Aucun timeout effectif en local

`llm_section_timeout = 86400` s. Un chunk qui part en boucle bloque le
traitement une journée entière. Le choix est assumé (§3.1), mais rien ne
détecte ni ne signale une génération anormalement longue.

### 9.6 Le moteur Mistral n'a aucun garde-fou structurel

Pas de JSON contraint, pas d'assemblage déterministe : si le modèle s'écarte du
plan demandé, le markdown produit s'en écarte aussi. Le seul filet est le
retrait du bloc de code englobant. En contrepartie, le modèle est bien plus
capable — le compromis est cohérent.

### 9.7 Aucun test automatisé

Comme les briques 1 et 2.

---

## 10. Vérifier

```powershell
& ".\meeting_assistant\Scripts\Activate.ps1"

# normalisation seule
python -m backend.run_app normalize transcript.txt transcript.normalized.txt

# moteur local (défaut)
$env:MEETING_PARTICIPANTS = "Marie Dupont, Jean Martin"
$env:MEETING_ENTREPRISES  = "YELE Consulting, RTE"
python -m backend.run_app minutes --transcript transcript.normalized.txt --output compte_rendu.md

# moteur Mistral
$env:MISTRAL_API_KEY = "..."
python -m backend.run_app mistral-minutes --transcript transcript.normalized.txt --output compte_rendu_mistral.md
```

**Points de contrôle :**

- `N chunks thématiques créés` — moins de 3 chunks sur une réunion d'une heure
  signale un découpage qui n'a pas fonctionné (transcript trop court, ou
  similarités trop uniformes). Plus de 15, un hachage excessif.
- Chaque chunk doit logger `résumé`, `extraction` **et** `plan` en mode
  perchunk. Deux seulement = mode legacy actif via `MEETING_PLAN_MODE`.
- `Plan d'attaque (perchunk) : N items assemblés … sans appel LLM final` —
  confirme le chemin déterministe.
- **Avant de tester une modification de prompt, supprimer
  `compte_rendu.sections.json`** (§9.2).
- Côté live, chercher `[LIVE][CHUNKER] ✂ Chunk #N fermé` puis
  `[LIVE][LLM] ✓ Chunk #N traité`. Un chunker qui ne ferme jamais rien produit
  un compte rendu vide au Stop.

---

## 11. Ce qui n'est PAS dans l'application

Le dépôt de travail contient des moteurs en cours de développement, **non
suivis par git et donc absents du build** :

| Élément | Fichiers | Nature |
|---|---|---|
| Orchestrateur agentique | `local_minutes.py`, `_bench_orchestrator.py` | remplaçant envisagé du moteur local : Context Builder → Planner → Content Designer → workers → juges |
| Assistant live Mistral | `live_advisor_worker.py`, `live_advisor_mistral.py`, `webapp/app/live-advisor/` | suggestions en temps réel pendant la réunion |
| Export DOCX | `convert_cr_to_docx.py` | conversion du compte rendu |

Deux fichiers **suivis** ont par ailleurs des modifications non commitées
substantielles : `mistral_minutes.py` (réécrit vers une architecture multi-passes
avec découpage, extraction, synthèse, rédaction) et `meeting_minutes_pipeline.py`
(ajustements de prompts). Ce document décrit les versions **livrées**.

---

## 12. Résumé pour une reprise

1. Trois chemins, un seul livrable `compte_rendu.md` : **live local**, **batch
   local**, **batch Mistral**.
2. Les deux chemins locaux **partagent tout** sauf le découpage — mêmes prompts,
   mêmes appels, même assemblage. Une modification de prompt affecte les deux.
3. **La structure du document est du code, pas du LLM.** Le modèle remplit des
   cases via des schémas JSON contraints au niveau des tokens ; les titres,
   tableaux et numérotations sont assemblés déterministiquement. C'est ce qui
   rend un modèle de 3B utilisable.
4. Les **entités figées** (participants, entreprises) sont ancrées deux fois
   dans le prompt pour corriger les erreurs phonétiques de l'ASR sur les noms
   propres.
5. Le **découpage sémantique** décide du plan : fenêtres de 3 phrases, chute de
   similarité MiniLM, seuil au percentile en batch, seuil glissant avec
   confirmation différée en live.
6. Le moteur Mistral est **structurellement différent** : un appel, aucun
   garde-fou de code, le plan dicté dans le prompt.
7. Les horodatages sont **supprimés** avant le LLM — le compte rendu n'a aucune
   notion de temps.

**Premier piège pour qui reprend :** le cache `compte_rendu.sections.json`
(§9.2). Il fait croire qu'une modification de prompt n'a pas d'effet.
