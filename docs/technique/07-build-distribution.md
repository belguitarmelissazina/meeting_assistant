# Brique 7 — Build & distribution

**Fichiers :** [build/backend.spec](../../build/backend.spec),
[electron/package.json](../../electron/package.json),
[electron/build-app.js](../../electron/build-app.js),
[electron/downloader.js](../../electron/downloader.js),
[electron/model_manifest.js](../../electron/model_manifest.js),
[scripts/prepare_assets.py](../../scripts/prepare_assets.py)
**Rôle :** transformer le dépôt en un installeur Windows, le publier, et le
mettre à jour sur les postes.

> Les **procédures opérationnelles** (commandes exactes, ordre des étapes,
> dépannage) sont déjà écrites dans [WORKFLOW.md](../../WORKFLOW.md) et
> [BUILD.md](../../BUILD.md). Ce document explique **comment c'est construit et
> pourquoi**, pas comment le lancer.

---

## 1. Ce que contient l'installeur — et ce qu'il ne contient pas

```
MeetingAssistant-Setup-X.Y.Z.exe          (~ 200 Mo)
│
├── app.asar                              ← files: dans package.json
│     main.js · preload.js · package.json
│     model_manifest.js · downloader.js · icônes
│
└── resources/                            ← extraResources:
      ├── backend/          ← dist/backend      (PyInstaller, un dossier)
      ├── webapp-out/       ← webapp/out        (export statique Next.js)
      ├── assets/bin/       ← bin/              (llama-server.exe)
      └── app-update.yml    ← écrit par electron-builder (contient le jeton READ)

    ✗ AUCUN modèle ML
```

**Les ~2,3 Go de modèles ne sont pas dans l'installeur.** Ils sont téléchargés
au premier lancement (§4). Le commentaire de
[backend.spec](../../build/backend.spec#L98) donne la raison :

> *Les fichiers de modèles volumineux ne sont pas empaquetés dans l'exe : ils
> partent en `extraResources` electron-builder pour que le même exe de 32 Mo
> n'ait pas besoin d'être reconstruit quand les modèles changent.*

Découplage utile : publier une nouvelle version de l'application ne réexpédie
pas 2,3 Go à chaque poste.

---

## 2. Le figeage du backend — PyInstaller

`pyinstaller build/backend.spec --noconfirm --clean` produit
`dist/backend/backend.exe` en **mode un-dossier** (`COLLECT`), avec
`console=True` — la console reste visible pour que les journaux du backend
soient lisibles.

Le point d'entrée est [backend/run_app.py](../../backend/run_app.py), le
dispatcher multi-mode (brique 4 §5.3).

### Trois catégories de dépendances à déclarer

**1. Paquets à collecter intégralement.** `collect_all()` sur seize paquets :
`sherpa_onnx`, `sounddevice`, `pyaudiowpatch`, `sentence_transformers`,
`wespeakerruntime`, `imageio_ffmpeg`, `onnxruntime`, `scipy`, `sklearn`,
`transformers`, `tokenizers`, `huggingface_hub`, `docx`, `silero_vad`, `msal`,
`msal_extensions`.

`silero_vad` porte un commentaire explicite : son sous-paquet `.data` contient
le modèle ONNX — c'est ce qui fait que le VAD est **embarqué dans l'exe**, à la
différence des deux autres modèles (brique 1 §5).

**2. Imports résolus par chaîne de caractères.** Uvicorn charge ses protocoles
et sa boucle d'événements par nom au démarrage :

```python
"uvicorn.lifespan.on", "uvicorn.protocols.http.auto",
"uvicorn.protocols.websockets.auto", "uvicorn.loops.auto", …
```

Sans ces déclarations, l'exe démarre puis **renvoie une erreur 500 à la première
requête**. Le commentaire du fichier le dit tel quel.

**3. Modules du projet appelés par sous-commande.**

```python
"backend", "backend.main", "backend.job_logger", "backend.resource_monitor",
"backend.graph_calendar", "audio_capture", "audio_capture.recorder",
"audio_capture.live_processor", "audio_capture.live_llm",
"diar_pipeline", "diar_pipeline.run", "diar_pipeline.audio", …
"normalize_transcript", "meeting_minutes_pipeline",
```

> ⚠ **Tout nouveau module doit être ajouté à cette liste.** `run_app.py` les
> atteint par `runpy.run_module` ou par import différé : l'analyse statique de
> PyInstaller ne les voit pas. Un module oublié produit un exe qui **se
> construit sans erreur et plante à l'exécution** — le pire des symptômes,
> puisque le build passe au vert.

### Exclusions

`matplotlib`, `tkinter`, `notebook`, `IPython`, `jupyter`, `PyQt5/6`,
`PySide2/6` — tirés transitivement par les paquets scientifiques, inutiles ici,
et coûteux en taille.

---

## 3. L'empaquetage Electron

`electron-builder`, cible **NSIS** Windows x64.

| Réglage | Valeur | Effet |
|---|---|---|
| `oneClick` | `false` | assistant d'installation, pas d'installation muette |
| `perMachine` | `false` | **installation par utilisateur** — pas de droits administrateur requis |
| `allowToChangeInstallationDirectory` | `false` | chemin imposé |
| `createDesktopShortcut` / `createStartMenuShortcut` | `true` | |
| `artifactName` | `MeetingAssistant-Setup-${version}.${ext}` | |

L'installation par utilisateur est cohérente avec le reste : les modèles vont
dans `userData`, les réglages dans `~/.meeting_assistant`. **Rien n'exige
d'élévation**, ce qui compte en environnement d'entreprise verrouillé.

> ⚠ **Aucune signature de code n'est configurée** — ni `certificateFile`, ni
> `forceCodeSigning`. L'installeur déclenche donc l'avertissement SmartScreen de
> Windows (« éditeur inconnu »), que chaque utilisateur doit contourner à la
> main. C'est le principal frein au déploiement à grande échelle, et cela se
> résout par l'achat d'un certificat, pas par du code.

### La version pilote tout

Le champ `version` de `package.json` alimente le nom de l'artefact, le tag de la
release, et la comparaison de l'auto-update. C'est **la seule valeur à
modifier** pour publier — `WORKFLOW.md` insiste : sans incrément, les postes
installés ne voient pas la nouvelle version.

---

## 4. Les modèles : téléchargement au premier lancement

### Le manifeste

[model_manifest.js](../../electron/model_manifest.js) — une liste statique, sans
aucun appel d'API pour la construire. Chaque entrée porte quatre champs :

| Champ | Rôle |
|---|---|
| `ghAsset` | nom de l'asset sur la release GitHub — **pas** une URL |
| `urlFallback` | URL directe HuggingFace |
| `relPath` | destination sous `userData/assets/` |
| `bytes` | taille exacte attendue — sert à la fois de vérification d'intégrité et de reprise |

Contenu : le LLM Ministral 3B (2,0 Go), les quatre fichiers de l'ASR (~68 Mo),
le ResNet34 d'embeddings (25 Mo), et les dix fichiers de MiniLM (~90 Mo).
Total ~2,3 Go.

Le commentaire précise que la liste MiniLM était auparavant énumérée via l'API
HuggingFace, et qu'elle a été figée : cela supprimait une dépendance réseau
supplémentaire, sur un point d'accès `/api/` souvent filtré par les pare-feux.

### Pourquoi GitHub en source primaire

> *URLs whitelistées par défaut dans 99 % des SI d'entreprise (les développeurs
> en ont besoin partout). Évite le filtrage des plateformes IA —
> `huggingface.co` est souvent bloqué chez les grands comptes.*

Et pourquoi un dépôt **privé** : ne pas rediffuser publiquement des modèles
tiers dont les licences ne couvrent pas forcément le miroir public, et réutiliser
le jeton en lecture déjà embarqué pour les mises à jour.

### La contrainte du dépôt privé

C'est le détail qui coûte le plus cher à redécouvrir :

> L'URL navigateur `github.com/OWNER/REPO/releases/download/TAG/FILE`
> **ne fonctionne pas** avec un jeton Bearer sur un dépôt privé — elle exige un
> cookie de session web et renvoie 404.

Le chemin correct, implémenté par `resolveGithubAssetMap()` :

```
1. GET api.github.com/repos/OWNER/REPO/releases/tags/assets-v1
      → liste des assets, chacun avec son `url` d'API
2. GET cette url avec Accept: application/octet-stream + Bearer
      → 302 vers une URL S3 signée → binaire
```

Le manifeste ne stocke donc que le **nom** de l'asset ; l'URL est résolue au
moment du téléchargement, puis mise en cache.

### `net` d'Electron, pas `https` de Node

C'est le choix technique le plus important de cette brique, et il est longuement
justifié en tête de [downloader.js](../../electron/downloader.js#L3).

La pile réseau de Chromium honore **automatiquement** :

- le proxy système, PAC et WPAD d'entreprise ;
- l'authentification proxy ;
- l'inspection SSL d'entreprise (certificats injectés dans le magasin Windows) ;
- le retrait de l'en-tête `Authorization` sur une redirection inter-domaines
  (`github.com` → `objects.githubusercontent.com`), comme le ferait un
  navigateur — **indispensable** pour les assets de dépôt privé.

Le commentaire résume : *« se comporte exactement comme Edge/Chrome, qui
marchent partout en entreprise »*, et cite le cas concret d'un client dont le
navigateur passe par un proxy alors que `https.get` de Node fait du direct — donc
bloqué par le pare-feu, donc expiration de délai.

### Robustesse du téléchargement

| Mécanisme | Détail |
|---|---|
| **Reprise** | en-tête `Range: bytes=N-` calculé sur la taille du fichier déjà présent — un incident à 1,8 Go du LLM ne repart pas de zéro |
| **Nouvelles tentatives** | 3 par fichier, avec attente croissante (2 s × numéro de tentative) |
| **Délai d'inactivité** | 120 s |
| **Intégrité** | comparaison de la **taille exacte** ; un fichier trop gros est supprimé et retéléchargé |
| **Reprise après coupure** | un fichier déjà à la bonne taille est ignoré |
| **Repli** | si GitHub échoue *ou* si l'asset est absent de la release → HuggingFace |

`allPresent()` vérifie présence **et** taille de tous les fichiers avant de
décider s'il y a quelque chose à télécharger.

> La source réellement utilisée (`github` ou `huggingface`) est remontée à la
> fenêtre de progression. Le commentaire explique pourquoi : *« utile pour
> vérifier en entreprise que GitHub passe bien et qu'on ne retombe pas
> silencieusement sur HF »*.

### En développement

`scripts/prepare_assets.py` télécharge MiniLM dans l'arborescence du dépôt, et
`ensureModelsDownloaded()` est un `no-op` — le mode développement pointe sur les
dossiers sources (brique 5 §3).

---

## 5. Les deux jetons GitHub

La séparation est stricte, et documentée en tête de
[build-app.js](../../electron/build-app.js#L5).

| Jeton | Droits | Où il vit | À quoi il sert |
|---|---|---|---|
| `GH_READ_TOKEN` | Contents **read-only** | injecté dans `app-update.yml`, donc **embarqué dans l'app** | télécharger les mises à jour **et** les modèles depuis le dépôt privé |
| `GH_TOKEN` | Contents **read + write** | uniquement `electron/.env` sur la machine de build | créer la release et téléverser les fichiers |

Les deux vivent dans `electron/.env`, **gitignoré**.

Le point subtil : `electron-builder` est invoqué avec `publish: "never"`. Il ne
contacte donc **jamais** GitHub. La configuration `publish` ne lui sert qu'à une
chose — graver le jeton de lecture dans `app-update.yml`. La publication réelle
est faite ensuite, à la main, par `publishToGitHub()` avec le jeton d'écriture.

C'est ce qui garantit que le jeton en écriture ne peut pas se retrouver dans le
paquet distribué.

> ⚠ **Le jeton de lecture, lui, est extractible de l'application** — c'est
> inévitable puisqu'elle doit s'authentifier seule. Le risque est borné par ses
> droits : lecture seule, sur un seul dépôt, qui ne contient que des installeurs
> et des modèles publics par ailleurs. À savoir, cependant : quiconque installe
> l'application peut lire ce dépôt.

---

## 6. La publication

`npm run publish` → `build:all` puis `node build-app.js --publish`.

```
1. build:python   → pyinstaller build/backend.spec
2. build:webapp   → next build (export statique)
3. electron-builder (publish: never)  → release/MeetingAssistant-Setup-X.Y.Z.exe
                                         + .blockmap + latest.yml
4. getOrCreateRelease()   → réutilise le tag s'il existe déjà
5. uploadAsset() × 3      → supprime l'homonyme puis téléverse
```

**L'opération est idempotente** : republier la même version réutilise la release
et remplace les assets, au lieu d'échouer ou de créer des doublons.

Les trois artefacts sont indispensables — `latest.yml` porte la version et
l'empreinte, `.blockmap` permet les mises à jour différentielles, `.exe` est
l'installeur.

---

## 7. La mise à jour automatique

Le mécanisme d'exécution est décrit en brique 5 §8. Côté distribution :

```
app-update.yml (dans resources/)
   provider: github · owner · repo · private: true · token: <READ>
        │
electron-updater interroge la release la plus récente
        │
   version publiée STRICTEMENT supérieure à l'installée ?
        └─ oui → téléchargement en fond → dialogue → quitAndInstall()
```

Deux conditions sine qua non, toutes deux rappelées dans `WORKFLOW.md` :

- **La version doit être incrémentée** dans `package.json`. Sans cela, aucun
  poste ne voit la nouveauté.
- **Les trois artefacts** doivent être présents sur la release.

Et une contrainte d'exécution : `stopBackendAndWait()` doit avoir tué
`backend.exe` **et** `llama-server.exe` avant que NSIS n'écrase les fichiers,
sinon l'installeur reste bloqué sur « Accès refusé » (brique 5 §3).

---

## 8. Les pièges du build

Documentés dans [WORKFLOW.md §3](../../WORKFLOW.md), ils reviennent à chaque
construction et ont tous la même cause : **OneDrive synchronise le dossier de
travail**.

| Symptôme | Cause | Correctif |
|---|---|---|
| Build webapp échoue sur `.next` (`EINVAL readlink`) | liens symboliques dans un dossier synchronisé | supprimer `webapp\.next` |
| PyInstaller échoue sur `dist\backend\_internal\...` (« Accès refusé ») | fichiers verrouillés ou en cours de synchro | supprimer `dist\`, `build\backend\` (garder `backend.spec`) ; tuer `backend.exe` / `llama-server.exe` |
| electron-builder échoue sur `release\` | idem | supprimer `release\` |
| Mise à jour figée sur le poste de test | processus encore vivants | terminer `Meeting Assistant`, `backend.exe`, `llama-server.exe` |

La procédure recommandée avant un build de publication : **suspendre la synchro
OneDrive** et supprimer les trois dossiers de sortie.

---

## 9. Limites connues

### 9.1 Aucune signature de code

Voir §3. SmartScreen avertit à chaque installation.

### 9.2 Le jeton de lecture est distribué avec l'application

Voir §5. Inhérent au modèle ; les droits sont volontairement minimaux.

### 9.3 L'intégrité des modèles repose sur la taille seule

Aucune empreinte cryptographique n'est vérifiée — seulement `bytes`. Un fichier
corrompu qui conserve la bonne taille passerait le contrôle. Le risque réel est
faible (HTTPS de bout en bout, source maîtrisée), mais une somme de contrôle
serait plus solide et le manifeste s'y prête déjà.

### 9.4 La liste des `hiddenimports` est une dette permanente

Voir §2. Elle doit être tenue à la main, et son oubli ne se voit qu'à
l'exécution.

### 9.5 Le build dépend d'un dossier synchronisé

Voir §8. Travailler hors du dossier OneDrive supprimerait toute cette catégorie
de problèmes.

### 9.6 Un seul test automatisé dans tout le projet

[electron/test_downloader.js](../../electron/test_downloader.js) couvre la
logique de repli du téléchargeur. C'est le **seul** test de l'application —
significatif que ce soit justement la partie la plus exposée aux réseaux
d'entreprise.

---

## 10. Résumé pour une reprise

1. L'installeur contient **le code, pas les modèles**. Les 2,3 Go sont
   téléchargés au premier lancement, ce qui découple la publication applicative
   des modèles.
2. Le backend est figé par PyInstaller avec **trois listes à tenir à la main** :
   paquets collectés, imports résolus par chaîne, modules du projet. Un oubli se
   voit à l'exécution, pas au build.
3. Le téléchargeur utilise **`net` d'Electron**, pas `https` de Node — c'est ce
   qui le fait fonctionner derrière un proxy d'entreprise, avec inspection SSL
   et redirection inter-domaines.
4. Un dépôt GitHub privé **impose de passer par l'API REST** ; l'URL de
   téléchargement navigateur renvoie 404 avec un jeton.
5. Deux jetons strictement séparés : le **lecture seule** est embarqué,
   le **écriture** ne quitte jamais la machine de build. `electron-builder` est
   lancé en `publish: "never"` précisément pour garantir cette séparation.
6. La **version de `package.json`** est la seule valeur à incrémenter pour
   publier ; sans elle, l'auto-update ne se déclenche pas.
7. Presque tous les échecs de build viennent de **OneDrive** qui verrouille les
   dossiers de sortie.

**Premier chantier si l'on veut fiabiliser le déploiement :** la signature de
code (§9.1). C'est le seul point qui dégrade l'expérience de **tous** les
utilisateurs, à chaque installation, et il ne se corrige pas dans le code.
