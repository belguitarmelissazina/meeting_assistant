# Brique 4 — Backend API (FastAPI)

**Fichiers :** [backend/main.py](../../backend/main.py) (~1 860 l., 28 endpoints),
[backend/graph_calendar.py](../../backend/graph_calendar.py),
[backend/job_logger.py](../../backend/job_logger.py),
[backend/resource_monitor.py](../../backend/resource_monitor.py),
[backend/run_app.py](../../backend/run_app.py)
**Rôle :** orchestrer les briques 1 à 3, exposer l'état à l'interface, et gérer
la persistance des réunions.

> **Périmètre.** Ce document décrit la version **livrée** (suivie par git). Le
> packaging du backend (PyInstaller, `backend.spec`) relève de la brique
> *Build & distribution*.

---

## 1. Ce que fait le backend — et ce qu'il ne fait pas

Le backend est un serveur FastAPI local, lié à **127.0.0.1 uniquement**, lancé
par Electron au démarrage de l'application. Il ne calcule presque rien
lui-même : il **orchestre des sous-processus** (briques 1 et 3), **héberge la
captation** (brique 2, qui tourne dans son propre processus), et **expose
l'état** à l'interface.

```
┌──────────────────────────────────────────────────────────────────┐
│ Electron  ──lance──►  backend.exe server   (127.0.0.1:8000)      │
│                                                                   │
│  Frontend Next.js ──HTTP──► FastAPI                              │
│                               │                                   │
│      ┌────────────────────────┼────────────────────────┐          │
│      ▼                        ▼                        ▼          │
│  captation live       sous-processus            système de       │
│  (dans le process)    backend.exe diar          fichiers          │
│  AudioRecorder        backend.exe normalize     Documents/        │
│  LiveProcessor        backend.exe minutes         Réunions/       │
│  (brique 2)           (briques 1 et 3)                            │
└──────────────────────────────────────────────────────────────────┘
```

**Il n'y a aucune base de données.** C'est le choix d'architecture le plus
structurant de cette brique, et tout le reste en découle (§2).

---

## 2. Le système de fichiers *est* la base de données

### 2.1 Où vivent les réunions

```
Documents/Réunions/                        ← HISTORY_DIR
├── 2026-05-19_14h00m00s_Revue produit/    ← une réunion
│   ├── audio.wav
│   ├── compte_rendu.md
│   ├── compte_rendu.docx
│   ├── transcript.txt
│   ├── turns.json
│   ├── speakers.json                      ← renommage des locuteurs
│   ├── .origin.recording                  ← marqueur : vient d'un enregistrement
│   └── .calendar_event.json               ← marqueur : réunion d'agenda liée
├── 2026-05-20_09h30m00s/                  ← une autre, hors agenda
└── Clients/                               ← une CATÉGORIE (sous-dossier réel)
    └── 2026-05-21_10h00m00s_Comité AO/    ← réunion classée dedans
```

Le chemin de `Documents` est résolu par l'API Windows `SHGetFolderPathW`
([main.py:87](../../backend/main.py#L87)) et non par `Path.home() /
"Documents"` — c'est ce qui permet de suivre le dossier réel quand **OneDrive
Known Folder Move** est actif, ce qui est le cas dans la plupart des
environnements d'entreprise.

### 2.2 Réunion ou catégorie ?

Il n'y a pas de métadonnée : la distinction est **déduite du contenu**
([main.py:267](../../backend/main.py#L267)) :

> Un dossier qui contient un fichier `audio.*` ou un `transcript.raw.txt` est
> une **réunion**. Sinon, c'est une **catégorie**.

Les « dossiers » de l'interface sont donc de vrais sous-dossiers de
`Documents/Réunions/`, sur **un seul niveau** de profondeur. L'utilisateur peut
les créer et les réorganiser directement dans l'Explorateur : l'application les
retrouvera au prochain démarrage.

### 2.3 Ce qui est rangé ailleurs

```
~/.meeting_assistant/
├── settings.json            ← clé API Mistral
├── graph_token_cache.bin    ← jetons Microsoft, chiffrés (DPAPI)
└── logs/
    ├── traitement_<label>.md   ← journal détaillé par traitement (dev)
    └── resource_*.csv          ← échantillonnage RAM (dev)
```

> **Rien de sensible ne va dans `Documents/`.** C'est délibéré : ce dossier est
> synchronisé par OneDrive. Y placer un *refresh token* Microsoft reviendrait à
> le répliquer dans le cloud et sur tous les postes de l'utilisateur.

---

## 3. Le modèle `Job`

Un `Job` ([main.py:195](../../backend/main.py#L195)) est un objet **purement en
mémoire** représentant une réunion.

| Champ | Sens |
|---|---|
| `status` | `draft` → `pending` → `queued` → `running` → `done` / `error` |
| `step` | libellé affiché dans l'interface (« Conversion + Diarisation… ») |
| `source` | `audio` ou `transcript` (import Teams) |
| `origin` | `recording` ou `upload` — pilote le mode de clustering (brique 1) |
| `out_dir` | le dossier de la réunion — **la seule donnée réellement persistante** |
| `context` | participants, entreprises, contexte, choix `local`/`mistral` |
| `calendar` | réunion d'agenda liée, ou `None` |
| `folder` | catégorie, ou `None` pour la racine |
| `created_at` | `st_ctime` du dossier — stable même après renommage |

> ⚠ **Les identifiants de job ne survivent pas à un redémarrage.** Ils sont
> générés par `uuid.uuid4()` au moment du rechargement
> ([main.py:299](../../backend/main.py#L299)). Un `job_id` n'est valable que
> pour la session en cours : il ne doit jamais être stocké côté frontend ni
> figurer dans une URL partagée.

---

## 4. Le rechargement au démarrage

```
import du module backend.main
   └─► thread daemon "rehydrate-jobs"        main.py:384
          parcourt Documents/Réunions/
          pour chaque dossier :
             réunion ?  → _load_job_from_dir()
             catégorie ? → parcourt ses sous-dossiers (1 niveau)
```

`_load_job_from_dir()` reconstruit le job à partir des seuls fichiers présents :
la présence de `compte_rendu.md` suffit à le marquer `done`, le marqueur
`.origin.recording` restitue l'origine, `.calendar_event.json` le lien à
l'agenda.

Deux points de conception :

**Le rechargement est lancé au niveau module, pas dans `@app.on_event("startup")`.**
Le commentaire l'explique : le scan lit **intégralement** chaque
`compte_rendu.md` et chaque `transcript.txt`, donc son coût croît avec
l'historique. En le déportant dans un thread daemon, uvicorn peut lier le port
immédiatement et `/api/health` répondre tout de suite — Electron n'attend pas.
Les réunions apparaissent progressivement, le frontend interrogeant `/api/jobs`
en continu.

**Un nettoyage rétroactif a lieu au passage.** `_load_job_from_dir` appelle
`_cleanup_intermediate_files` sur les réunions terminées : les anciens dossiers
encombrés de fichiers intermédiaires sont épurés au premier démarrage suivant la
mise à jour.

> ⚠ **Tout l'historique reste en mémoire.** `job.report_markdown` et
> `job.transcript` contiennent le texte **complet** de chaque réunion, et
> `/api/jobs` les renvoie tous à chaque appel — que l'interface les affiche ou
> non. L'empreinte mémoire et la taille des réponses croissent linéairement avec
> le nombre de réunions archivées.

---

## 5. L'orchestration du pipeline

### 5.1 Un traitement à la fois

```python
async def run_pipeline(job):
    job.status = "queued"
    async with pipeline_lock:          # asyncio.Lock global
        job.status = "running"
        _prevent_sleep()
        try:    await _run_pipeline_locked(job)
        finally: _allow_sleep()
```

Le verrou est **global au processus** : deux réunions ne peuvent jamais être
traitées simultanément. C'est cohérent avec la nature du travail — un
llama-server qui sature déjà le CPU, et la collision de fichiers temporaires
signalée en brique 1 §4.1.

`_prevent_sleep()` appelle `SetThreadExecutionState(ES_CONTINUOUS |
ES_SYSTEM_REQUIRED)` : sans ça, un portable se mettrait en veille au milieu d'un
traitement de vingt minutes.

### 5.2 L'enchaînement

`_run_pipeline_locked` ([main.py:571](../../backend/main.py#L571)) :

```
source = audio ?
   ├─ transcript.txt déjà présent (CR live) → on saute la diarisation
   └─ sinon → backend.exe diar  [--bootstrap-online si origin=recording]
                renomme {stem}.transcript.midpoint.txt → transcript.txt
                renomme {stem}.turns.json              → turns.json
source = transcript ?
   └─ on part directement du fichier importé

→ backend.exe normalize   transcript.txt → transcript.normalized.txt
→ backend.exe minutes | mistral-minutes  → compte_rendu.md
→ _md_to_docx()                          → compte_rendu.docx
→ _cleanup_intermediate_files()
→ status = done
```

### 5.3 Pourquoi des sous-processus

`_subcmd()` ([main.py:558](../../backend/main.py#L558)) construit l'invocation
selon le mode :

| Mode | Commande |
|---|---|
| Figé (PyInstaller) | `backend.exe <sous-commande> …` — le même exe se rappelle lui-même |
| Développement | `python -m backend.run_app <sous-commande> …` |

Deux raisons cumulées : **l'isolation mémoire** (la diarisation et le LLM
montent à plusieurs Go, le processus meurt et rend tout), et le fait qu'un exe
figé **ne peut pas** exécuter `python -m foo.bar`.

`_run_subprocess` lit la sortie ligne par ligne et la réémet préfixée du
`job_id`, avec un filet en cas de console restée en cp1252. L'environnement est
propagé par `{**os.environ, …}` — c'est ce qui transmet `SHERPA_DIR`,
`PRETRAINED_DIR` et consorts aux briques 1 et 3.

### 5.4 Le nettoyage

`_cleanup_intermediate_files` ([main.py:724](../../backend/main.py#L724)) ne
conserve que sept fichiers :

```
audio.<ext>   compte_rendu.md   compte_rendu.docx   .calendar_event.json
transcript.txt   turns.json   speakers.json
```

Tout le reste — transcript normalisé, `words.json`, RTTM, métriques, sections —
est supprimé. Le dossier étant visible par l'utilisateur dans l'Explorateur (et
synchronisé par OneDrive), il doit rester lisible.

---

## 6. Les 28 endpoints

### Santé et paramètres

| Endpoint | Rôle |
|---|---|
| `GET /api/health` | sonde utilisée par Electron pour savoir quand afficher la fenêtre |
| `GET /api/settings` | renvoie `mistralKeySet` (booléen) — **jamais la clé** |
| `PUT /api/settings` | enregistre ou efface la clé Mistral |

### Calendrier Microsoft — §7

`GET /api/calendar/status` · `POST /api/calendar/login` ·
`POST /api/calendar/logout` · `GET /api/calendar/upcoming`

### Enregistrement — brique 2

`POST /api/record/start` · `POST /api/record/stop` · `GET /api/record/status` ·
`POST /api/record/cancel`

`recorder` et `live_processor` sont des variables **globales** : un seul
enregistrement à la fois. `record/start` réinitialise automatiquement un état
resté coincé plutôt que de renvoyer une erreur, et `record/cancel` existe pour
le cas de l'enregistrement fantôme après un arrêt raté.

### Import

| Endpoint | Rôle |
|---|---|
| `POST /api/process/upload` | fichier audio → `<dossier>/audio.<ext>` |
| `POST /api/process/upload-transcript` | `.txt` ou `.docx` Teams → `transcript.raw.txt` (§9) |

### Cycle de vie d'un job

| Endpoint | Rôle |
|---|---|
| `POST /api/jobs/{id}/process` | lance le traitement en tâche de fond |
| `GET /api/jobs` | tous les jobs, triés par date décroissante |
| `GET /api/jobs/{id}` | un job |
| `PATCH /api/jobs/{id}` | renommer — refusé si `queued`/`running` |
| `DELETE /api/jobs/{id}` | supprimer le dossier — refusé si en cours |
| `POST /api/jobs/{id}/open-folder` | ouvrir dans l'Explorateur |

> **`/process` est idempotent** ([main.py:1500](../../backend/main.py#L1500)) :
> si le job est déjà `done` et que `compte_rendu.md` existe, il répond
> `alreadyDone: true` sans rien relancer. C'est ce qui permet au compte rendu
> produit en live d'être simplement constaté.

### Contenus

| Endpoint | Rôle |
|---|---|
| `GET /api/jobs/{id}/audio` | flux audio pour le lecteur intégré |
| `GET /api/jobs/{id}/turns` | tours de parole + mapping des noms |
| `PATCH /api/jobs/{id}/speakers` | renommer les locuteurs |
| `GET /api/jobs/{id}/download` | `?kind=report` (docx) ou `?kind=transcript` |
| `PATCH /api/jobs/{id}/report` | enregistrer le markdown édité, **régénère le DOCX** |

Le renommage des locuteurs mérite une note : le mapping est stocké à part, dans
`speakers.json`. **`turns.json` n'est jamais modifié** — les étiquettes
`SPEAKER_XX` y restent la source de vérité, et le frontend applique le mapping
au rendu. Un renommage est donc toujours réversible : une valeur vide retire
l'entrée.

### Dossiers (catégories)

| Endpoint | Rôle |
|---|---|
| `GET /api/folders` | liste des catégories |
| `POST /api/folders` | créer — 409 si le nom existe |
| `DELETE /api/folders/{name}` | supprimer — 409 si elle contient des réunions |
| `POST /api/jobs/{id}/folder` | déplacer une réunion (`null` = racine) |

Le déplacement est un vrai `shutil.move` du dossier, suivi de la réécriture de
tous les chemins mémorisés dans le job (`out_dir`, `audio_path`, `report_path`,
`report_docx_path`, `transcript_path`).

---

## 7. Le calendrier Microsoft

[backend/graph_calendar.py](../../backend/graph_calendar.py) — intégration
Microsoft Graph pour proposer les réunions à venir au moment de démarrer un
enregistrement.

**Modèle d'authentification : *device code flow*, client public.**

```
POST /api/calendar/login
   └─► MSAL initie un device flow
          → renvoie un code + une URL à l'utilisateur
   └─► thread daemon : acquire_token_by_device_flow()  (bloquant, ~15 min max)
          l'interface interroge GET /api/calendar/status
```

Trois conséquences importantes :

- **Aucun secret n'est embarqué dans le binaire distribué.** Un client public
  n'en a pas besoin ; il n'y a donc rien à extraire de l'exe.
- **Permission déléguée `Calendars.Read` uniquement.** Chaque salarié se
  connecte avec son propre compte et l'application ne voit que son agenda. Ce
  n'est pas une application de service qui lirait les agendas de tous.
- **Le flux est bloquant**, d'où le thread daemon et le *polling* de `status()`
  par l'interface plutôt qu'une réponse HTTP qui resterait ouverte un quart
  d'heure.

Les jetons sont mis en cache dans `~/.meeting_assistant/graph_token_cache.bin`,
chiffré par `msal-extensions` (DPAPI sous Windows, donc lié au compte Windows).

`CLIENT_ID` et `TENANT_ID` sont en dur avec surcharge possible par
`GRAPH_CLIENT_ID` / `GRAPH_TENANT_ID` — prévu pour un futur passage
multi-tenant.

Toutes les fonctions du module sont **synchrones** (msal et requests le sont) ;
les endpoints les appellent via `asyncio.to_thread`.

---

## 8. Markdown → DOCX

`_md_to_docx()` ([main.py:820](../../backend/main.py#L820)) est un convertisseur
**écrit à la main**, sans dépendance de conversion : il lit le markdown ligne
par ligne et pilote `python-docx`.

Il gère un peu plus que ce que produit la brique 3 :

| Markdown | Style Word |
|---|---|
| `#` … `######` | `add_heading(level=n)` |
| `- ` / `* ` | `List Bullet` |
| `1. ` | `List Number` |
| `> ` | `Intense Quote` |
| ` ``` ` | bloc de code |
| tableau GFM | tableau Word, via `_render_table` |
| `**gras**`, `*italique*` | *runs* en ligne, via `_add_inline_runs` |

Les tableaux sont détectés par la conjonction `_is_table_row(ligne)` **et**
`_is_table_separator(ligne suivante)` — c'est la règle GitHub-flavored, et elle
évite de confondre un tableau avec une ligne contenant des barres verticales.

`_unescape_md()` annule les échappements markdown (`1\.` → `1.`) — nécessaire
parce que l'assemblage de la brique 3 échappe les pipes dans les cellules de
tableau.

La conversion est déclenchée deux fois : en fin de traitement, et à chaque
`PATCH /api/jobs/{id}/report` quand l'utilisateur édite le compte rendu.

---

## 9. Import d'un transcript Teams

`_parse_teams_docx_transcript()` ([main.py:977](../../backend/main.py#L977))
convertit un export Teams `.docx` vers le format interne
`Locuteur: texte`. Il reconnaît les horodatages de la forme `12:34` ou `1:23:45`
et les lignes de nom de participant.

Ce chemin saute entièrement les briques 1 et 2 : le job est créé avec
`source="transcript"`, et le pipeline part directement à la normalisation.

---

## 10. Journalisation et monitoring

| Module | Produit | Où |
|---|---|---|
| `job_logger.py` | `traitement_<label>.md` — chronologie détaillée d'un traitement, étape par étape, avec récapitulatif | `~/.meeting_assistant/logs/` |
| `resource_monitor.py` | `resource_*.csv` — échantillonnage RAM toutes les 30 s | idem |

> **Les deux sont désactivés dans le build distribué**
> ([main.py:71](../../backend/main.py#L71)). En mode figé, `_LOGS_ENABLED` et
> `_RAM_MONITOR_ENABLED` valent `False` et **aucune variable d'environnement
> standard ne les réactive** — les utilisateurs finaux n'écrivent rien dans leur
> dossier personnel. Seule une trappe non documentée, `MEETING_DEV_LOGS=1`,
> permet de déboguer une installation packagée.
>
> En développement, les deux sont actifs par défaut, désactivables par
> `MEETING_JOB_LOG=0` / `MEETING_RAM_MONITOR=0`.

Le journal d'accès d'uvicorn est désactivé (`access_log=False` dans
`run_app.py`) parce que le frontend interroge `/api/jobs` en continu. Un
middleware maison, `_log_errors_only`, ne journalise que les erreurs.

---

## 11. Les contraintes Windows / OneDrive

Une part notable du code de cette brique n'existe que pour ça.

### Suppression de fichiers verrouillés

`_force_rmtree()` ([main.py:139](../../backend/main.py#L139)) réessaie après
`chmod(S_IWRITE)` — l'attribut lecture seule est fréquent sur les `.docx`
synchronisés — et **renvoie la liste des chemins qui ont résisté**.

`DELETE /api/jobs/{id}` s'en sert pour répondre **423 Locked** avec un message
actionnable (« Fermez Word / l'Explorateur… ») plutôt qu'une erreur générique.
Et surtout : **le job est remis en mémoire** si la suppression a échoué, pour
que l'interface ne montre pas une réunion disparue qui existe encore sur disque.

### Téléchargement

`GET /download` lit le fichier **en mémoire** avant de répondre, précisément
pour transformer un `PermissionError` en 423 explicite plutôt qu'en 500 opaque.

### Noms de fichiers

`_sanitize_label()` ([main.py:773](../../backend/main.py#L773)) retire les
caractères interdits (`<>:"/\|?*`), les caractères de contrôle, les points et
espaces en fin de nom, préfixe les noms réservés (`CON`, `PRN`, `COM1`…) et
tronque à 200 caractères.

### Ouvrir l'Explorateur

`subprocess.Popen(["explorer", …])` et non `os.startfile` : un processus en
arrière-plan n'a pas le droit de passer au premier plan, mais `explorer.exe` si.
La fenêtre s'affiche donc réellement devant, et réutilise celle déjà ouverte sur
ce dossier.

---

## 12. Limites connues

### 12.1 Les identifiants de job ne sont pas stables

Voir §3. Régénérés à chaque démarrage.

### 12.2 Tout l'historique est en mémoire et renvoyé à chaque appel

Voir §4. `GET /api/jobs` renvoie le markdown et le transcript intégraux de
**toutes** les réunions — et le frontend l'interroge **toutes les 2,5 secondes**
([useJobs.ts:15](../../webapp/lib/useJobs.ts#L15)). Avec 50 réunions d'une heure
archivées, cela représente plusieurs mégaoctets sérialisés en JSON toutes les
2,5 secondes, que l'interface en affiche une seule ou aucune.

La correction naturelle serait de retirer `reportMarkdown` et `transcript` de la
charge utile de la liste, et de les servir uniquement par
`GET /api/jobs/{id}` — qui existe déjà et renvoie exactement la même structure.

### 12.3 Un seul enregistrement, un seul traitement

Variables globales pour la captation, `pipeline_lock` pour le traitement. C'est
un choix cohérent pour une application de bureau mono-utilisateur, mais rien
n'est prévu pour en sortir.

### 12.4 Aucune authentification sur l'API

Le serveur est lié à `127.0.0.1`, donc inaccessible depuis le réseau. Mais
**tout processus tournant sur la machine** peut appeler ses endpoints, y compris
lire les comptes rendus et déclencher un enregistrement. Acceptable pour une
application de bureau ; à savoir avant d'exposer le port.

### 12.5 Le CORS accepte `null` et toute origine `file://` / `app://`

Nécessaire parce qu'Electron charge le frontend depuis `file://`. Combiné au
point précédent, cela signifie qu'une page web locale malveillante pourrait
dialoguer avec l'API.

### 12.6 Catégories sur un seul niveau

`_rehydrate_jobs` ne descend que d'un cran. Une réunion rangée dans un
sous-sous-dossier par l'utilisateur **disparaît** de l'application, sans erreur —
elle reste sur disque mais n'est plus listée.

### 12.7 Aucun test automatisé

Comme les briques précédentes.

---

## 13. Vérifier

```powershell
& ".\meeting_assistant\Scripts\Activate.ps1"
python -m backend.run_app server        # 127.0.0.1:8000

# dans un autre terminal
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/jobs
curl http://127.0.0.1:8000/api/folders
```

FastAPI expose aussi la documentation interactive sur
`http://127.0.0.1:8000/docs` — pratique pour parcourir les 28 endpoints et
leurs schémas sans lire le code.

**Points de contrôle :**

- `Dossier des réunions : <chemin>` au démarrage — vérifie que
  `SHGetFolderPathW` a bien trouvé le dossier suivi par OneDrive, et non un
  `Documents` local vide.
- `Historique rechargé : N réunion(s)` — arrive **après** que le port réponde,
  c'est normal (§4). Si `/api/jobs` est vide pendant quelques secondes au
  démarrage, le scan n'est pas terminé.
- `Debug toggles : job_log=…, ram_monitor=… (frozen=…)` — confirme le mode.
- Un `423` sur une suppression ou un téléchargement n'est pas un bug : c'est le
  code qui signale un fichier verrouillé par Word ou OneDrive (§11).

---

## 14. Résumé pour une reprise

1. **Aucune base de données.** Le système de fichiers fait foi :
   `Documents/Réunions/`, un dossier par réunion, des marqueurs cachés pour les
   métadonnées. L'état en mémoire est reconstruit à chaque démarrage.
2. Une réunion se distingue d'une catégorie par la **présence d'un fichier
   `audio.*` ou `transcript.raw.txt`**, rien d'autre.
3. Les **identifiants de job sont éphémères** — régénérés à chaque lancement.
4. Le rechargement de l'historique tourne dans un **thread daemon** pour ne pas
   retarder l'ouverture de l'application, mais charge tout en mémoire.
5. Le backend **n'exécute pas** les briques 1 et 3 : il les lance en
   sous-processus via le dispatcher `run_app.py`, pour l'isolation mémoire et
   parce qu'un exe figé ne peut pas lancer `python -m`.
6. Un **verrou global** garantit un seul traitement à la fois, et la mise en
   veille est bloquée pendant.
7. Les données sensibles (clé Mistral, jetons Microsoft) sont **hors de
   `Documents/`** pour ne pas être synchronisées par OneDrive.
8. Une part notable du code existe pour absorber les **fichiers verrouillés par
   Word et OneDrive** — d'où les réponses `423` et le `_force_rmtree` avec
   retry.

**Premier point à surveiller si l'usage s'intensifie :** `GET /api/jobs` renvoie
l'intégralité des comptes rendus et transcripts de tout l'historique, à chaque
appel, en boucle (§12.2).
