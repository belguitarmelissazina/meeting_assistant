# Brique 1 — Diarisation + transcription

**Package :** `diar_pipeline/`
**Rôle :** transformer un fichier audio en transcript attribué par locuteur.

> **Périmètre.** Ce document décrit le traitement de l'audio : les étapes du
> pipeline, les modèles, les algorithmes, les réglages. Le déploiement de cette
> brique (packaging PyInstaller, téléchargement des modèles au premier
> lancement, injection des chemins par Electron) relève de la brique
> *Build & distribution* et n'est pas traité ici.
>
> Le package contient aussi du code issu de la phase de benchmark (méthodes de
> clustering alternatives, raffinement VBx, tracking MLflow, backends
> d'embedding secondaires) : rien de tout cela n'est appelé en production et
> rien n'est documenté ici. Voir §10.

---

## 1. Rôle de la brique

Entrée : un fichier audio quelconque (m4a, mp3, wav, webm… tout ce que ffmpeg
sait décoder).
Sortie : un transcript texte horodaté, chaque tour de parole préfixé par un
identifiant de locuteur.

```
audio.m4a  ──►  [diar_pipeline]  ──►  transcript.txt
                                      [00:03.20 - 00:11.45]  SPEAKER_00 : bonjour à tous...
                                      [00:11.45 - 00:19.02]  SPEAKER_01 : oui, sur le point deux...
```

Deux propriétés structurantes :

1. **Tout est local.** Aucun appel réseau pendant le traitement. Trois modèles,
   tous exécutés sur CPU (§5).
2. **Transcribe-first.** La transcription tourne sur l'audio *entier* avant la
   diarisation, et l'attribution des locuteurs se fait *a posteriori* en
   recollant les mots aux segments. Ce n'est pas l'ordre habituel — §3.

---

## 2. Quand la brique est appelée

L'application ne diarise pas systématiquement. Trois cas :

| Cas | Brique exécutée ? | Mode de clustering |
|---|---|---|
| Fichier audio **uploadé** | ✅ oui | **batch** (§4.5) |
| **Enregistrement** dans l'app, pipeline live OK | ❌ court-circuitée | — |
| **Enregistrement**, pipeline live en échec | ✅ en repli | **bootstrap + online** (§4.5) |
| Transcript texte uploadé | ❌ non | — |

Le court-circuit tient en une condition : si un `transcript.txt` non vide
existe déjà dans le dossier du job — produit par le pipeline live pendant la
captation — toute la brique est sautée
([backend/main.py:607](../../backend/main.py#L607)). Le pipeline live n'écrit ce
fichier **que** s'il a réussi, précisément pour rendre ce repli possible.

**En pratique, la brique sert donc surtout aux fichiers uploadés.**

L'application l'invoque avec exactement trois arguments :

```
diar  -i <dossier job>/audio.<ext>  -o <dossier job>  [--bootstrap-online]
```

Le dernier n'est ajouté que si `job.origin == "recording"`
([backend/main.py:615](../../backend/main.py#L615)). Ni `--num-speakers` ni
`--no-diarize` ne sont jamais passés : le nombre de locuteurs est toujours
estimé, et la diarisation toujours active.

### Second consommateur : le pipeline live

[audio_capture/live_processor.py](../../audio_capture/live_processor.py) (brique
*Capture audio*) importe directement trois morceaux internes du package :

| Importé | Depuis |
|---|---|
| `BootstrapOnlineClusterer` | `clustering.py` |
| `_EmbeddingExtractor` | `embeddings.py` |
| `align_words_to_speakers`, `words_to_turns`, `format_transcript_txt`, `Segment` | `transcription.py`, `models.py` |

Il réimplémente en revanche sa propre boucle ASR et son propre
`_build_segments`.

> ⚠ **`run.py` n'est donc pas le seul consommateur de ces fonctions.** Modifier
> `_EmbeddingExtractor` ou `BootstrapOnlineClusterer` casse le mode live sans
> qu'aucun test ni aucun import visible dans `diar_pipeline` ne le signale.

---

## 3. Le pipeline

Orchestré par [`main()` dans run.py:57](../../diar_pipeline/run.py#L57),
exécution strictement séquentielle — aucun parallélisme entre étapes.

```
  ┌─────────────────────────────────────────────────────────────────┐
  │ [1] CONVERSION AUDIO                            audio.py         │
  │     ffmpeg → WAV 16 kHz mono                                     │
  └───────────────────────────┬─────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                            ▼
  ┌─────────────────────────┐         ┌──────────────────────────────┐
  │ [2] ASR                 │         │ [3] VAD              vad.py  │
  │     transcription.py    │         │  Silero → zones de parole    │
  │  sherpa-onnx Zipformer  │         └───────────────┬──────────────┘
  │  streaming FR (kroko)   │                         │ list[SpeechSegment]
  │  → mots + timestamps    │                         ▼
  │                         │         ┌──────────────────────────────┐
  │  ⚠ tourne sur l'audio   │         │ [4] EMBEDDINGS embeddings.py │
  │  ENTIER, sans découpage │         │  fenêtre glissante 1.2s/0.6s │
  └───────────┬─────────────┘         │  WeSpeaker ResNet34-LM       │
              │                       │  → matrice (N, 256)          │
              │                       └───────────────┬──────────────┘
              │                                       ▼
              │                       ┌──────────────────────────────┐
              │                       │ [5] CLUSTERING clustering.py │
              │                       │  NMESC estime k              │
              │                       │  Spectral Clustering assigne │
              │                       │  → labels (N,)               │
              │                       └───────────────┬──────────────┘
              │                                       ▼
              │                       ┌──────────────────────────────┐
              │                       │ [6] SEGMENTS    segments.py  │
              │                       │  fusion des segments voisins │
              │                       └───────────────┬──────────────┘
              │                                       │ list[Segment]
              └───────────────┬───────────────────────┘
                              ▼
              ┌───────────────────────────────────────┐
              │ [7] ALIGNEMENT MOTS ↔ LOCUTEURS       │
              │     transcription.py                  │
              └───────────────────────────────────────┘
                              │
                              ▼
                       transcript.txt + turns.json
```

### Pourquoi « transcribe-first »

L'approche classique découpe l'audio selon la diarisation, puis transcrit
chaque segment séparément. Ici c'est l'inverse : un seul passage ASR sur tout
l'audio, puis recollage.

**Avantage :** le modèle ASR est *streaming* et conserve son contexte sur toute
la réunion — pas de mots coupés ni perdus aux frontières de segments, et un
seul chargement de modèle.

**Coût :** l'attribution du locuteur devient un problème de recollage temporel,
résolu approximativement (§4.7). Aux chevauchements de parole, le transcript ne
contient qu'une voix, attribuée à un seul locuteur.

---

## 4. Traitement de l'audio, étape par étape

### 4.1 Conversion — `audio.py`

`convert_to_wav()` normalise l'entrée : **16 kHz, mono, WAV**, via le ffmpeg
embarqué dans le paquet pip `imageio-ffmpeg` (pas de dépendance à un ffmpeg
système).

```
ffmpeg -y -v error -i <source> -ac 1 -ar 16000 <temp>/{stem}_16k.wav
```

Le 16 kHz mono n'est pas un choix de confort : c'est le format d'entraînement
des trois modèles (Silero, ResNet34, Zipformer). Tout écart dégrade la qualité.

> ⚠ **L'audio source est décodé deux fois.** `convert_to_wav(in_path)` produit
> le WAV utilisé par le VAD et les embeddings ; puis `load_audio_pcm(in_path)`
> relance ffmpeg **sur le fichier d'origine** pour produire le PCM float32
> destiné à l'ASR ([run.py:89 et 103](../../diar_pipeline/run.py#L89)). Deux
> passes ffmpeg complètes sur le même fichier. Le WAV converti aurait pu servir
> aux deux.

> ⚠ Le WAV converti est écrit dans le dossier temporaire du système et **jamais
> supprimé**. Or le backend nomme toujours le fichier source `audio.<ext>` —
> `audio.wav` pour un enregistrement
> ([main.py:1349](../../backend/main.py#L1349)), `audio{ext}` pour un upload
> ([main.py:1452](../../backend/main.py#L1452)). **Tous les jobs écrivent donc
> au même chemin temporaire** (`audio_16k.wav`). Sans conséquence tant que les
> jobs sont sérialisés — ce qu'assure `pipeline_lock`
> ([main.py:546](../../backend/main.py#L546)) — mais c'est une hypothèse
> implicite à connaître avant d'envisager le moindre parallélisme.

### 4.2 Transcription — `transcription.py`

`transcribe()` instancie un `sherpa_onnx.OnlineRecognizer` **transducteur**
(encoder / decoder / joiner + `tokens.txt`) :

| Réglage | Valeur |
|---|---|
| `num_threads` | 4 |
| `sample_rate` | 16 000 |
| `feature_dim` | 80 |
| `decoding_method` | `greedy_search` |
| `enable_endpoint_detection` | `False` |

L'audio est poussé dans le stream **par tranches de 0,5 s**, chaque tranche
décodée jusqu'à épuisement (`while rec.is_ready(stream)`). En fin de fichier,
0,5 s de silence est ajouté pour vider le buffer du décodeur — sans quoi les
derniers mots seraient perdus.

La détection de fin de phrase est **désactivée** : on veut un flux continu sur
toute la réunion, pas une segmentation par le modèle ASR.

**Reconstruction des mots.** `_tokens_to_words()` réassemble les tokens BPE :

- le marqueur SentencePiece `U+2581` (ou une espace) signale un **début de
  mot** → on clôture le mot en cours et on en ouvre un nouveau ;
- un token sans marqueur est **collé** au mot en cours ;
- la ponctuation (`.` `,` `!` `?` `:` `;` `...`) est recollée au mot précédent,
  et la fin de ce mot est repoussée de `+0,08 s`.

Sortie : une liste de `{word, start, end}`.

### 4.3 Détection de parole — `vad.py`

Silero VAD découpe le WAV en zones de parole. Paramètres effectifs (fixés dans
`run.py`, différents des défauts du module) :

| Paramètre | Valeur | Effet |
|---|---|---|
| `threshold` | `0.4` | probabilité de parole minimale (défaut module : 0.45) |
| `min_speech_duration_ms` | `200` | ignore les salves de parole < 200 ms |
| `min_silence_duration_ms` | `50` | ne coupe pas sur un silence < 50 ms |
| `speech_pad_ms` | `20` | marge ajoutée de part et d'autre de chaque zone |

Sortie : une liste de `SpeechSegment(start, end)` — **sans locuteur**. Le VAD
répond « quelqu'un parle », pas « qui parle ».

> ⚠ **`silero_vad.read_audio` est délibérément contourné**
> ([vad.py:57](../../diar_pipeline/vad.py#L57)). La fonction officielle tire
> `torchaudio>=2.11` + `torchcodec`, deux dépendances lourdes et pénibles à
> figer sous PyInstaller. On lit le WAV avec `soundfile` et on construit le
> tenseur nous-mêmes — possible parce que l'étape 4.1 garantit déjà du 16 kHz
> mono float32. Un rééchantillonnage linéaire de secours subsiste dans la
> fonction, au cas où elle serait appelée sur un WAV non converti.

### 4.4 Empreintes vocales — `embeddings.py`

Chaque zone de parole est découpée en fenêtres, et chaque fenêtre passée au
modèle d'embedding qui en extrait un vecteur **256-d** caractérisant la voix.

**Règle de fenêtrage** ([embeddings.py:142](../../diar_pipeline/embeddings.py#L142)) :

| Durée de la zone | Traitement |
|---|---|
| < 0,4 s | **ignorée** — aucun embedding produit |
| < 1,8 s (= `win_len × 1.5`) | **une seule fenêtre** couvrant toute la zone |
| ≥ 1,8 s | fenêtre glissante de **1,2 s**, pas de **0,6 s** (50 % de recouvrement) ; la dernière fenêtre est tronquée à la fin de la zone |

Le compromis derrière `1,2 s` : trop court, l'empreinte vocale est instable ;
trop long, on risque d'englober deux locuteurs dans la même fenêtre. Le
recouvrement de 50 % limite le second effet sans multiplier le coût.

Ordre de grandeur : **une réunion d'une heure avec 80 % de parole produit
~4 800 embeddings**. Cette valeur pilote tout le coût du clustering (§8).

**Deux chemins d'extraction :**

- `extract(wav_path)` — le mode batch écrit **un fichier WAV temporaire par
  fenêtre**, le passe au modèle, puis le supprime. Soit ~4 800 cycles
  create/write/read/unlink.
- `extract_from_array(pcm, sr)` — utilisé par le **mode live**. `wespeaker`
  exigeant un chemin de fichier, un **seul** temporaire est créé puis réécrit à
  chaque appel. Le commentaire du code annonce un facteur ~5 sur l'overhead
  disque Windows. Le mode batch pourrait l'utiliser, mais ne le fait pas (§8).

Sortie : une matrice `(N, 256)` et la liste des `SubSegment` correspondants
(chacun sachant de quelle zone VAD il provient, via `parent_idx`).

### 4.5 Regroupement des voix — `clustering.py`

Deux questions : *combien de locuteurs ?* puis *quel locuteur pour chaque
embedding ?*

Chemin exécuté en production :

```
cluster_speakers(emb, method="sc", enhance=True, estimate_method="nmesc")
    │
    ├─ normalisation L2 des embeddings
    ├─ k = estimate_speakers_nmesc(emb)          ← combien de locuteurs
    └─ labels = cluster_sc(emb, k, enhance=True)  ← qui est qui
```

#### Estimation du nombre de locuteurs — NME-SC

[clustering.py:191](../../diar_pipeline/clustering.py#L191) — réimplémentation
fidèle de l'algorithme 1 de **Park et al. 2020**, *Auto-Tuning Spectral
Clustering*.

Le problème : pour regrouper les voix, on construit un graphe de similarité
entre embeddings, et il faut décider combien de voisins garder par nœud. Ce
paramètre change le résultat, et il n'y a pas de bonne valeur universelle.
L'idée de NME-SC est de **balayer ce paramètre et de retenir celui qui produit
la structure la plus nette**.

Pour chaque `p` (nombre de voisins conservés par ligne) :

1. `Ap = binarize(A, p)` — on garde les `p` plus fortes similarités par ligne ;
2. `Āp = (Ap + Apᵀ)/2` — symétrisation ;
3. `Lp = D − Āp` — laplacien non normalisé ;
4. décomposition en valeurs propres ;
5. `ep` = écarts entre valeurs propres consécutives, plafonnés à `max_k` ;
6. `gp = max(ep) / λ_max` — la valeur NME ;
7. `r[p] = p / gp`.

Puis `p̂ = argmin(r)` et **`k = argmax(e_p̂) + 1`** — le nombre de locuteurs est
lu dans le plus grand saut entre valeurs propres consécutives (*eigengap*).

Balayage : `p` de 1 à `0,25 × N`, échantillonné en **30 valeurs** au plus. Un
contrôle de connexité suit : si le graphe à `p̂` n'est pas connexe, on remonte
le balayage jusqu'au premier `p` qui l'est.

Bornes : `k` est ramené dans `[1, 20]`.

> ⚠ **Décomposition dense obligatoire**
> ([clustering.py:250](../../diar_pipeline/clustering.py#L250)). Le code utilise
> `scipy.linalg.eigh` dense, pas `eigsh` (ARPACK), alors qu'ARPACK serait bien
> plus rapide puisqu'on ne veut que les plus petites valeurs propres. Raison
> documentée dans le code : **ARPACK n'est pas déterministe sous BLAS
> multi-thread** et faisait basculer le `k` estimé d'un run à l'autre sur un
> audio identique — cas cité : FR-069, `k` oscillant entre 3 et 5, DER passant
> de 0,13 à 0,27. Le dense est plus lent mais stable bit-à-bit. **Ne pas
> « optimiser » ce point sans reproduire d'abord ce test.**

> ⚠ **Le BLAS doit être forcé en mono-thread avant tout import de numpy.** Même
> cause, même combat que le point précédent : sous BLAS multi-thread, `eigh`
> donne des résultats variables d'un run à l'autre, et le nombre de locuteurs
> estimé change sur un audio identique.
>
> ```python
> for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
>            "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
>     _os.environ.setdefault(_v, "1")
> ```
>
> Ce bloc est présent **trois fois** —
> [`diar_pipeline/__init__.py`](../../diar_pipeline/__init__.py#L1),
> [`diar_pipeline/run.py`](../../diar_pipeline/run.py#L21) et
> [`backend/run_app.py`](../../backend/run_app.py#L28) — parce que chacun de ces
> fichiers peut être le premier point d'entrée selon le chemin d'appel. Il
> **doit** s'exécuter avant l'import de numpy/scipy : une fois le BLAS chargé,
> ces variables n'ont plus aucun effet.
>
> C'est aussi pour cette raison que le balayage sur `p` est **séquentiel** et
> non parallélisé (`# parallelization causes BLAS oversubscription on Windows`)
> — et donc que la diarisation n'exploite qu'un seul cœur sur ses étapes les
> plus lourdes.

#### Raffinement de la matrice d'affinité — `sim_enhancement`

[clustering.py:62](../../diar_pipeline/clustering.py#L62) — appliqué avant le
clustering (`enhance=True` en production). Objectif : réduire le bruit entre
locuteurs dans la matrice de similarité. Sept étapes, dans l'ordre :

`diagonal_fill` → `gaussian_blur(σ=1)` → `row_threshold_mult(p=0.95, ×0.01)` →
`symmetrization` → `diffusion (A·Aᵀ)` → `row_max_norm` → `symmetrization`

> ⚠ La **symétrisation finale** n'est pas décorative : `row_max_norm` casse la
> symétrie, et le laplacien exige une matrice symétrique. Le commentaire
> `# <-- final symmetrization` marque exactement ça.

#### Assignation — Spectral Clustering

[clustering.py:301](../../diar_pipeline/clustering.py#L301) — Spectral
Clustering scikit-learn sur affinité précalculée, `assign_labels="kmeans"`,
`random_state=42`. La similarité cosinus, naturellement dans `[-1, 1]`, est
ramenée dans `[0, 1]` par `(cos + 1) / 2`.

#### Mode « bootstrap + online »

[clustering.py:648](../../diar_pipeline/clustering.py#L648) — activé par
`--bootstrap-online`, donc pour les **enregistrements faits dans
l'application**.

1. NMESC + Spectral Clustering classique sur les **1 000 premiers embeddings**
   (≈ 10 minutes à un pas de 0,6 s) ;
2. calcul des centroïdes par locuteur et d'un **seuil cosinus auto-calibré** :
   point milieu entre le p10 des similarités intra-cluster et le p90 des
   similarités inter-cluster, borné à `[0.3, 0.85]` (`_calibrate_threshold`) ;
3. le reste des embeddings est assigné séquentiellement au centroïde le plus
   proche, avec mise à jour incrémentale de ce centroïde.

Sous 1 000 embeddings, la fonction retombe silencieusement sur le clustering
batch.

**Pourquoi ce mode existe :** il évite de faire tourner NMESC (coût cubique) sur
l'intégralité d'une longue réunion, et il fournit une logique compatible avec le
streaming, où l'on n'a pas la vue globale de l'audio.

#### `BootstrapOnlineClusterer` — la variante live

[clustering.py:731](../../diar_pipeline/clustering.py#L731) — version *stateful*
de la même idée, alimentée embedding par embedding via `.add()`. Utilisée
uniquement par le pipeline live, documentée ici parce qu'elle partage le code
ci-dessus.

> ⚠ **Le « freeze » post-bootstrap est un correctif, pas une simplification.**
> Après la phase de bootstrap, la classe **n'ajoute plus jamais de nouveau
> locuteur** : tout embedding est attribué au centroïde bootstrap le plus
> proche. Sans cette contrainte, les embeddings bruités (fenêtres de 1,2 s mal
> filtrées par le VAD) ne ressemblaient à aucun centroïde et créaient des faux
> locuteurs en série — **dérive observée de 5 à plus de 25 locuteurs sur une
> réunion d'une heure**. Le seuil ne sert plus qu'à décider si l'on met à jour
> le centroïde (match propre) ou non (match faible : on assigne sans polluer).
>
> **Hypothèse assumée :** tous les locuteurs parlent dans les 10 premières
> minutes. Vrai en pratique sur des réunions professionnelles (tour de table).
> Un participant arrivant en retard est rattaché au locuteur acoustiquement le
> plus proche — compromis accepté.

### 4.6 Construction des segments — `segments.py`

`build_segments()` transforme les étiquettes par fenêtre en segments de parole
continus :

1. chaque `SubSegment` devient un triplet `(start, end, SPEAKER_XX)` ;
2. les zones VAD **sans embedding** (celles de moins de 0,4 s, écartées en 4.4)
   récupèrent le locuteur du sous-segment le plus proche dans le temps —
   recherche par force brute ;
3. tri chronologique, puis **fusion** des segments consécutifs de même locuteur
   séparés de moins de `merge_gap = 0,7 s`.

Ce dernier point évite un transcript haché : sans lui, une micro-pause au milieu
d'une phrase produirait deux tours de parole distincts pour le même locuteur.

### 4.7 Alignement mots ↔ locuteurs — `transcription.py`

C'est ici que les deux branches du pipeline se rejoignent : d'un côté les mots
horodatés (4.2), de l'autre les segments avec locuteur (4.6).

`align_words_to_speakers()` — dite **midpoint** — procède mot par mot : on prend
l'**instant médian** du mot `(start + end) / 2` et on cherche le segment de
diarisation qui le contient. Si le mot tombe dans un trou entre deux segments,
on prend le plus proche des deux. Le balayage utilise un curseur `last_idx`
conservé d'un mot au suivant, donc le coût reste linéaire.

`words_to_turns()` regroupe ensuite les mots consécutifs de même locuteur en
tours `{start, end, speaker, text}`, et `format_transcript_txt()` produit le
`.txt` final horodaté.

> `run.py` calcule **aussi** une seconde stratégie, `align_words_by_boundaries`
> : au lieu de décider mot par mot, elle relève les instants de changement de
> locuteur et cale chacun sur le `.`, `!` ou `?` le plus proche dans une fenêtre
> de ±5 s. L'intention est bonne — un changement de locuteur tombe rarement au
> milieu d'une phrase — mais sa sortie est écrite sur disque et **jamais lue**.
> C'est du temps de calcul et trois fichiers pour rien à chaque job (§8).

---

## 5. Modèles utilisés

Trois modèles, tous en **ONNX sur CPU**, tous attendant du 16 kHz mono.

| Modèle | Étape | Rôle | Sortie | Taille |
|---|---|---|---|---|
| **Silero VAD** | [3] | détecter les zones de parole | intervalles `(start, end)` | ~0,6 Mo |
| **kroko streaming Zipformer FR** — `encoder` + `decoder` + `joiner` + `tokens.txt` | [2] | transcription française | tokens BPE + timestamps | ~67,7 Mo |
| **WeSpeaker ResNet34-LM** (VoxCeleb) | [4] | empreinte vocale | vecteur 256-d | ~25,3 Mo |

Points à connaître :

- **Le Zipformer est *streaming*, pas *offline*.** C'est ce qui permet de
  l'alimenter par tranches de 0,5 s tout en gardant le contexte, et c'est le
  même modèle qui sert au pipeline live. Un modèle offline donnerait sans doute
  une meilleure qualité en batch, au prix de perdre cette mutualisation.
- **Le ResNet34 est entraîné sur VoxCeleb**, corpus majoritairement anglophone.
  Les empreintes vocales restent discriminantes quelle que soit la langue —
  c'est la voix qui est modélisée, pas le contenu — mais ce n'est pas un modèle
  spécialisé français, contrairement à l'ASR.
- **Aucun des trois n'est fine-tuné** sur les données du projet.

**Résolution des chemins.** Le code cherche le modèle ASR dans la variable
d'environnement `SHERPA_DIR`
([transcription.py:22](../../diar_pipeline/transcription.py#L22)) et les
embeddings dans `PRETRAINED_DIR`
([embeddings.py:23](../../diar_pipeline/embeddings.py#L23)), avec repli sur les
dossiers du dépôt source. Ces variables sont renseignées par l'application —
voir la brique *Build & distribution*.

> ⚠ **Le ResNet34 est chargé depuis un chemin ONNX explicite, jamais via
> `lang="en"`** ([embeddings.py:66](../../diar_pipeline/embeddings.py#L66)).
> L'API `wespeaker_rt.Speaker(lang="en")` déclencherait un téléchargement
> HuggingFace au premier appel — impossible dans une application qui tourne
> hors-ligne.

---

## 6. Configuration effective

Toute la configuration réelle est **codée en dur** en tête de
[run.py:43-54](../../diar_pipeline/run.py#L43). Il n'y a ni fichier de config,
ni réglage exposé dans l'interface.

```python
EMBED_MODEL          = "resnet34"    # embeddings 256-d
ESTIMATE_METHOD      = "nmesc"       # estimation du nombre de locuteurs
CLUSTER_METHOD       = "sc"          # spectral clustering
ENHANCE              = True          # sim_enhancement activé
WIN_LEN              = 1.2           # fenêtre d'embedding (s)
HOP_LEN              = 0.6           # pas d'embedding (s)
VAD_MODEL            = "silero"
VAD_THRESHOLD        = 0.4
VAD_MIN_SPEECH_MS    = 200
VAD_MIN_SILENCE_MS   = 50
VAD_PAD_MS           = 20
```

Pour ajuster le VAD ou le fenêtrage, il faut **modifier le code**. C'est un
choix assumé — un seul jeu de réglages validé — mais c'est le premier point de
friction pour qui veut faire varier le comportement.

---

## 7. Fichiers produits

Avec `-o <dossier job>` sur un fichier source `audio.m4a` (`file_id = "audio"`) :

| Fichier | Consommé par |
|---|---|
| `audio.transcript.midpoint.txt` | ✅ **le backend** → renommé `transcript.txt`, puis normalisé et envoyé au LLM |
| `audio.turns.json` | ✅ **le backend** → renommé `turns.json`, alimente la vue Transcript synchronisée à l'audio |
| `audio.words.json`, `audio.words_midpoint.json`, `audio.turns_midpoint.json`, `audio.words_per_speaker.json` | ❌ débogage |
| `audio.words_boundary.json`, `audio.turns_boundary.json`, `audio.transcript.boundary.txt` | ❌ stratégie d'alignement non retenue (§4.7) |
| `audio.rttm`, `audio.diarization.txt` | ❌ évaluation hors app / inspection manuelle |

**2 fichiers sur 10 sont réellement utilisés.** Les 8 autres restent dans le
dossier de réunion de l'utilisateur, qui les voit dans l'Explorateur via
« Ouvrir le dossier ».

Le format `.rttm` est le standard NIST de la diarisation : c'est lui qui permet
de calculer un DER contre une référence annotée, si l'on veut mesurer la
qualité.

---

## 8. Limites connues

### 8.1 Coût cubique du clustering batch

`estimate_speakers_nmesc` effectue une décomposition dense sur une matrice
`N × N`, **pour chacune des 30 valeurs de `p`**. Le coût croît donc en `O(N³)`.
`cluster_sc` ajoute une seconde décomposition du même ordre.

| Durée de réunion | N embeddings (≈80 % de parole) | Coût relatif |
|---|---|---|
| 10 min | ~800 | 1× |
| 30 min | ~2 400 | ~27× |
| 60 min | ~4 800 | ~216× |

*(Extrapolation depuis la complexité algorithmique — pas un benchmark mesuré.)*

Le mode `--bootstrap-online` résout exactement ce problème en plafonnant NMESC à
1 000 embeddings. **Mais il n'est appliqué qu'aux enregistrements**, pas aux
fichiers uploadés — qui sont pourtant les plus susceptibles d'être longs, et les
seuls pour lesquels la brique tourne systématiquement (§2).

C'est le principal risque de performance. Trois pistes, par coût croissant :

1. passer `--bootstrap-online` aussi pour les uploads au-delà d'un seuil de
   durée — une ligne dans [backend/main.py:615](../../backend/main.py#L615) ;
2. sous-échantillonner les embeddings donnés à NMESC (l'estimation de `k` n'a
   pas besoin de la résolution complète), puis clusteriser sur l'ensemble ;
3. réduire le nombre de valeurs de `p` balayées — gain seulement linéaire.

### 8.2 Chevauchements de parole

Perdus par construction (§3). Le VAD ne détecte pas la parole simultanée, un
embedding sur une fenêtre à deux voix est un mélange, et l'ASR ne transcrit
qu'un flux. Quand deux personnes se coupent, le transcript en garde une.

### 8.3 Travail calculé pour rien

- **Alignement `boundary`** (§4.7) : calculé à chaque job, 3 fichiers écrits,
  zéro consommateur. Soit le brancher, soit le retirer.
- **Double décodage ffmpeg** (§4.1) : deux passes complètes sur le fichier
  source.
- **Fichiers temporaires d'embedding** (§4.4) : ~4 800 cycles disque en batch,
  alors que `extract_from_array()` existe déjà.

### 8.4 Points mineurs

- `build_segments` cherche le plus proche voisin par force brute — sans impact
  tant que les zones < 0,4 s restent rares.
- Collision de fichiers temporaires sur `audio_16k.wav` (§4.1).
- **Aucun test automatisé** ne couvre cette brique. La vérification est
  manuelle.

---

## 9. Lancer et vérifier

```powershell
& ".\meeting_assistant\Scripts\Activate.ps1"

# exactement ce que fait l'app sur un fichier uploadé
python -m diar_pipeline.run -i "reunion.m4a" -o ".\_test_diar"

# exactement ce que fait l'app sur un enregistrement (repli live)
python -m diar_pipeline.run -i "reunion.m4a" -o ".\_test_diar" --bootstrap-online

# debug : force k et court-circuite NMESC — bien plus rapide sur un long fichier
python -m diar_pipeline.run -i "reunion.m4a" --num-speakers 4
```

**Forme de la sortie console** (valeurs illustratives — la brique n'a pas de
chiffres de référence mesurés et versionnés) :

```
============================================================
  DIARISATION + TRANSCRIPTION — reunion.m4a
============================================================
  [1] audio -> reunion_16k.wav (….…s)  ….…s
  [2] Transcription (sherpa-onnx)...
        10.0% | …s/…s | RTF ….…x        ← progression tous les 10 %
      -> N words  ….…s
  [3] VAD: N segments  ….…s
  [4] Embeddings: N x 256  ….…s          ← la dimension DOIT être 256
  [5] Clustering (batch): K speakers  ….…s
  [6] Aligning N words to K speakers...
      midpoint: N turns | boundary: N turns | speakers: {...}
============================================================
  DONE
============================================================
  Duration / Speakers / Words / Time (RTF global) / Output
```

**Points de contrôle :**

- `[4]` doit annoncer une dimension **256**. Autre chose = mauvais backend
  d'embedding, ou ONNX introuvable.
- `[5]` renvoyant `1 speaker` sur une réunion multi-locuteurs signale presque
  toujours un problème de qualité audio en amont (capture d'un seul micro,
  audio système non capté), pas un bug du clustering.
- Le `RTF` affiché en `[2]` est celui de l'ASR seul. Le RTF global, en fin de
  run, inclut le clustering — c'est lui qui explose sur les longs fichiers
  (§8.1).
- Sortie attendue par l'app : `{stem}.transcript.midpoint.txt` **et**
  `{stem}.turns.json`. Si le premier manque, le backend lève
  `FileNotFoundError` et le job échoue
  ([backend/main.py:624](../../backend/main.py#L624)).

---

## 10. Ce qui n'est PAS utilisé

Le package contient du code hérité de la phase de recherche. Il n'est appelé par
aucun chemin de l'application et ne doit pas être pris pour de la logique de
production :

- `refinement.py` (raffinement VBx) et `tracking.py` (MLflow, DER, silhouette,
  UMAP) — deux fichiers entiers, jamais importés par `run.py` ;
- dans `clustering.py` : `estimate_speakers_gmm_bic`, `cluster_ahc`,
  `cluster_ahc_threshold`, `cluster_meanshift`, `cluster_cosine_greedy` ;
- dans `vad.py` : le backend `pyannote` (exigerait un token HuggingFace) ;
- dans `embeddings.py` : les backends `campplus` (512-d) et `ecapa` (192-d) —
  leurs checkpoints ONNX ne sont pas livrés, les sélectionner échouerait ;
- `align_words_by_boundaries` — seule exception : il **est** exécuté à chaque
  run, mais sa sortie n'est consommée par personne (§4.7).

Ces éléments ont servi à choisir la configuration actuelle et resservent si un
choix doit être rejustifié. Les supprimer est possible, mais n'apporte rien à
l'application.

---

## 11. Résumé pour une reprise

1. Le pipeline est **transcribe-first** : ASR sur tout l'audio, puis recollage
   des locuteurs par instant médian de chaque mot. Les chevauchements de parole
   sont perdus par construction.
2. La brique **ne tourne pas systématiquement** : elle est court-circuitée dès
   que le pipeline live a produit un `transcript.txt`. En pratique elle sert
   surtout aux **fichiers uploadés**.
3. Trois modèles ONNX sur CPU, aucun fine-tuné : Silero (VAD), Zipformer FR
   *streaming* (ASR), WeSpeaker ResNet34 VoxCeleb (empreintes vocales).
4. Le cœur algorithmique est **NMESC** (Park et al. 2020) pour estimer le nombre
   de locuteurs, puis **Spectral Clustering** pour les assigner.
5. Le pipeline live **importe directement des morceaux internes** du package
   (`BootstrapOnlineClusterer`, `_EmbeddingExtractor`). Aucun test ne protège ce
   contrat.
6. La configuration est **en dur dans `run.py`** ; l'application ne passe que 3
   arguments.
7. Les contraintes signalées ⚠ sont des correctifs de bugs reproduits — le code
   les justifie en commentaire, les défaire fait revenir le bug.

**Premier chantier si l'on doit améliorer quelque chose :** le coût cubique du
clustering batch sur les fichiers uploadés longs (§8.1). La correction la moins
risquée tient en une ligne côté backend.
