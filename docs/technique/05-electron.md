# Brique 5 — Shell Electron

**Fichiers :** [electron/main.js](../../electron/main.js) (~1 430 l.),
[electron/preload.js](../../electron/preload.js) (72 l.)
**Rôle :** héberger l'application — cycle de vie du backend, fenêtres, icône de
barre des tâches, notifications natives.

> **Périmètre.** Ce document couvre ce que fait le shell **à l'exécution**. Le
> packaging (electron-builder, `extraResources`), le téléchargement des modèles
> au premier lancement et la publication des versions relèvent de la brique
> *Build & distribution*. L'auto-update figure ici uniquement pour le mécanisme
> d'arrêt qu'il impose au backend (§7).

---

## 1. Ce qu'est vraiment ce shell

Electron n'affiche pas seulement une fenêtre : il est le **superviseur de
processus** de l'application. Il démarre le backend Python, attend qu'il soit
prêt, lui transmet les chemins des modèles, le tue proprement à la sortie, et
continue de vivre en arrière-plan même quand l'utilisateur ferme la fenêtre.

```
                 ┌────────────────────────────────────────────┐
                 │  process Electron (main.js)                 │
                 │                                             │
   utilisateur ──┤  fenêtre principale ──HTTP──┐               │
                 │  splash                     │               │
                 │  popup du tray              │               │
                 │  icône barre des tâches     │               │
                 │  notifications natives      │               │
                 │                             ▼               │
                 │  spawn ────────────► backend.exe server     │
                 │                       127.0.0.1:8000        │
                 └────────────────────────────────────────────┘
```

Point à retenir : **le frontend parle au backend en HTTP direct**, pas par IPC.
Le préchargement n'expose qu'une URL (`backendUrl`) et quelques canaux
d'événements ; toutes les données transitent par l'API de la brique 4.

---

## 2. La séquence de démarrage

Onze étapes, dans un ordre qui compte
([main.js:1348](../../electron/main.js#L1348)).

```
app.requestSingleInstanceLock()      ← une seule instance ; la 2ᵉ réveille la 1ʳᵉ
   │
app.whenReady()
   │
   1. await ensureModelsDownloaded()   ← bloquant, fenêtre de progression dédiée
   2. await showSplash()               ← visible en < 1 s
   3. startBackend()                   ← spawn de backend.exe
   4. await waitForBackend()           ← /api/health, 90 s max
   5. createWindow()                   ← remplace le splash à `ready-to-show`
   6. setupAutoUpdate()                ← production uniquement
   7. await loadUserPrefs()
   8. setupTray()
   9. setupMeetingNotifications()
  10. setupCrReadyNotifications()
  11. --hidden ? → masquer au tray
```

Toute exception dans cette chaîne ferme le splash, affiche une boîte d'erreur
et quitte — plutôt que de laisser une fenêtre vide.

### Le splash n'est pas cosmétique

Le démarrage à froid du backend figé (chargement de Python, numpy, torch, ONNX)
prend plusieurs secondes. Sans splash, l'utilisateur double-clique et ne voit
rien. La séquence est donc : afficher **d'abord** une fenêtre légère, démarrer
le backend **ensuite**, et ne créer la vraie fenêtre qu'une fois `/api/health`
opérationnel.

Le HTML du splash et celui de la fenêtre de téléchargement sont **écrits en
ligne dans `main.js`** et chargés en *data URI* — pas de fichier supplémentaire
à packager, pas d'étape de build pour deux écrans statiques.

### La bascule splash → fenêtre principale

```js
let revealed = false;
const reveal = () => {
  if (revealed) return;      // idempotent
  revealed = true;
  if (mainWindow && !mainWindow.isVisible()) mainWindow.show();
  closeSplash();
};
mainWindow.once("ready-to-show", reveal);
revealTimer = setTimeout(reveal, 8000);   // filet de sécurité
```

La fenêtre est créée avec `show: false` pour ne jamais peindre de blanc : elle
apparaît et le splash disparaît dans la même frame.

> ⚠ **L'idempotence de `reveal()` corrige un bug précis**, expliqué en
> commentaire : sans le drapeau `revealed`, le filet de sécurité à 8 secondes
> rappellerait `show()` après coup. Or une fenêtre **réduite** est
> `isVisible() === false` — l'application se serait donc dé-minimisée toute
> seule huit secondes après le démarrage.

---

## 3. Le cycle de vie du backend

### Démarrage

`startBackend()` ([main.js:86](../../electron/main.js#L86)) construit
l'environnement du processus fils — c'est le point de passage de toute la
configuration de déploiement :

```js
MODELS_DIR, SHERPA_DIR, PRETRAINED_DIR, LLAMA_BIN_DIR, MINILM_DIR
HF_HUB_OFFLINE = "1"   TRANSFORMERS_OFFLINE = "1"   PYTHONIOENCODING = "utf-8"
BACKEND_HOST = "127.0.0.1"   BACKEND_PORT = "8000"
```

| Mode | Commande | Répertoire de travail |
|---|---|---|
| Développement | `python -u -m backend.run_app server` | racine du dépôt |
| Production | `backend.exe server` | dossier de l'exe |

`windowsHide: true` évite la fenêtre de console noire. Les deux flux de sortie
sont relayés vers ceux d'Electron, préfixés `[backend]`.

### Attente de disponibilité

`waitForBackend()` interroge `/api/health` toutes les 500 ms, avec un délai
d'expiration par requête de 2 s et un plafond global de **90 secondes**.

> ⚠ Sur une machine lente ou un premier démarrage après mise à jour (cache de
> fichiers froid, antivirus qui inspecte un exe fraîchement écrit), ces 90
> secondes peuvent être dépassées. L'application affiche alors « Le démarrage a
> échoué » et quitte — sans distinguer un backend lent d'un backend cassé.

### Arrêt

Deux fonctions, pour deux besoins.

**`stopBackend()`** — `treeKill(pid, SIGTERM)`. L'arbre entier, pas le seul
processus racine : uvicorn engendre des processus fils, et `llama-server.exe`
en est un. Un `SIGTERM` sur la racine seule **laisse des orphelins** sous
Windows.

**`stopBackendAndWait(timeoutMs = 6000)`** — même chose en `SIGKILL`, mais
renvoie une promesse résolue à la mort effective du processus, avec un plafond
de 6 secondes.

> ⚠ **Cette seconde variante existe à cause d'un gel observé en production.**
> L'ancien code appelait `stopBackend()` puis `quitAndInstall()` immédiatement.
> Tant que `backend.exe` et `llama-server.exe` tiennent les fichiers,
> l'installeur NSIS reste bloqué sur l'écrasement de
> `resources/backend/_internal/*` — « Accès refusé », mise à jour figée. Le
> plafond de 6 secondes est délibéré : mieux vaut une mise à jour qui continue
> qu'une application bloquée sur sa boîte de dialogue.

---

## 4. La fenêtre principale

```js
new BrowserWindow({
  width: 1280, height: 800, minWidth: 900, minHeight: 600,
  show: false, backgroundColor: "#0b0b0f",
  webPreferences: {
    preload: "preload.js",
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
  },
})
```

La posture de sécurité est celle recommandée : **isolation du contexte activée,
intégration Node désactivée, bac à sable actif**. Le renderer n'a aucun accès à
Node ; il ne voit que ce que le préchargement expose explicitement (§5).

Quatre comportements notables :

- **Le titre est verrouillé.** `page-title-updated` est annulé, sinon le
  `<title>` de la page Next.js écraserait « Meeting Assistant ».
- **Les liens externes s'ouvrent dans le navigateur système**, via
  `setWindowOpenHandler` qui refuse systématiquement l'ouverture interne.
- **La recherche dans la page** (`Ctrl+F` sur un compte rendu) passe par
  `webContents.findInPage`, piloté depuis le renderer par IPC. Le choix est
  expliqué en commentaire : cela fonctionne quel que soit le mode de rendu —
  markdown affiché ou éditeur `contenteditable`.
- **Fermer la fenêtre ne quitte pas l'application** — §6.

---

## 5. Le pont de préchargement

[preload.js](../../electron/preload.js) expose un unique objet
`window.electronAPI`, sans jamais donner accès à `require` ni à `ipcRenderer`
directement.

| Clé | Contenu |
|---|---|
| `backendUrl` | `http://127.0.0.1:8000` |
| `find` | `start` / `stop` / `onResult` — recherche dans la page |
| `notifications` | `onOpenMeeting` — clic sur une notification d'agenda |
| `tray` | `onOpenJob`, `onFirstHideHint`, `notifySettingsChanged` |
| `trayWindow` | `openMainApp`, `quitApp`, `startRecording`, `stopRecording` |

Chaque abonnement renvoie **sa propre fonction de désabonnement**, pour que les
composants React nettoient leurs écouteurs au démontage :

```js
onOpenJob: (cb) => {
  const h = (_e, payload) => cb(payload);
  ipcRenderer.on("tray:open-job", h);
  return () => ipcRenderer.removeListener("tray:open-job", h);
}
```

> Les boutons de la popup du tray **délèguent toutes leurs actions au processus
> principal** plutôt que d'appeler l'API directement. Le commentaire l'explique :
> sinon il faudrait dupliquer la logique (notifications natives, ouverture de la
> fenêtre, gestion d'état) entre la popup et le menu contextuel.

---

## 6. Le mode barre des tâches

C'est le comportement par défaut, en **retrait volontaire** (*opt-out*) : fermer
la fenêtre **cache** l'application au lieu de la quitter. Le processus Electron
et le backend continuent de tourner — sans quoi les notifications et
l'enregistrement depuis la barre des tâches cesseraient de fonctionner.

```js
mainWindow.on("close", (e) => {
  if (isQuitting || userPrefs.quitOnClose) return;   // fermeture réelle
  e.preventDefault();
  mainWindow.hide();
  mainWindow.webContents.send("tray:first-hide-hint");
});
```

Le drapeau `isQuitting` est posé par le bouton « Quitter » du menu et par
`before-quit`. Le réglage `quitOnClose` rétablit le comportement classique.

**La première fois**, le renderer reçoit `tray:first-hide-hint` et affiche une
explication — sinon l'utilisateur croit avoir quitté alors que l'application
tourne encore.

### L'icône et son menu

L'icône a deux états : normale, et **avec une pastille rouge superposée**
pendant un enregistrement, composée à l'exécution
(`makeTrayIcon`, [main.js:933](../../electron/main.js#L933)).

Le menu contextuel est reconstruit dynamiquement selon l'état :

| Situation | Entrées |
|---|---|
| Enregistrement en cours | durée écoulée (désactivée) · « Arrêter et générer le compte rendu » |
| Au repos | « Démarrer un enregistrement (hors agenda) » |
| Au repos, réunion d'agenda dans moins de 15 min | raccourci dédié : « Démarrer pour *sujet* (14:00) », avec participants et contexte pré-remplis |

Puis toujours « Ouvrir Meeting Assistant » et « Quitter ».

### La popup

Un second niveau d'interface : une `BrowserWindow` sans bordure de 340 × 480,
ancrée à l'icône, qui charge la route Next.js `/tray-popup`. Elle offre les
mêmes actions dans une présentation riche.

### Lancement au démarrage de Windows

`applyLaunchAtStartup()` utilise `app.setLoginItemSettings` avec l'argument
`--hidden`. Au démarrage de session, l'application se réduit donc directement
dans la barre des tâches au lieu d'ouvrir sa fenêtre — présente « au cas où »,
sans s'imposer.

---

## 7. Les notifications

Trois mécanismes indépendants, tous pilotés par le processus principal.

### « Compte rendu prêt »

`pollCrReadyOnce()` interroge `/api/jobs` **toutes les 5 secondes** et détecte
la transition `running → done` en comparant avec l'ensemble des jobs vus en
cours au tour précédent. Un `Set` évite de notifier deux fois le même job. Le
clic ramène la fenêtre au premier plan et envoie `tray:open-job` au renderer.

### Rappel 5 minutes avant une réunion

`pollUpcomingForNotifications()` interroge `/api/calendar/upcoming?days=1`
**toutes les 5 minutes**, et programme un `setTimeout` pour chaque réunion
commençant dans l'heure. Deux structures évitent les doublons :
`scheduledNotifs` (réunion → identifiant de minuteur, pour ne pas reprogrammer
au tour suivant) et `notifiedIds` (réunions déjà notifiées).

### Rappel de fin de réunion

Programmé à l'heure de fin déclarée dans l'agenda, uniquement pour un
enregistrement rattaché à une réunion ayant une heure de fin future — un
enregistrement hors agenda n'en a pas.

### `AppUserModelId`

```js
app.setAppUserModelId("com.yele.meeting-assistant");
```

Sans cette ligne, les notifications Windows s'affichent sous le nom
`electron.app.Default` avec l'icône par défaut. Elle doit correspondre à
l'`appId` déclaré pour l'empaquetage.

---

## 8. La mise à jour automatique

`setupAutoUpdate()` ([main.js:1285](../../electron/main.js#L1285)) — `no-op` en
développement.

```
autoDownload = true            → téléchargement en fond, sans rien demander
autoInstallOnAppQuit = true    → installation au prochain arrêt

on("update-downloaded") → boîte de dialogue « Redémarrer maintenant / Plus tard »
                            └─ si oui : await stopBackendAndWait()   ← §3
                                        autoUpdater.quitAndInstall()
```

> ⚠ **Toutes les erreurs de mise à jour sont silencieuses** — seulement
> journalisées en console. C'est délibéré (« un poste hors-ligne ne doit pas
> bloquer l'application »), mais la conséquence est qu'un poste qui ne se met
> jamais à jour — jeton expiré, proxy bloquant, dépôt inaccessible — ne le
> signale nulle part. Rien dans l'interface ne montre la version installée ni la
> date de la dernière vérification.

---

## 9. La compatibilité réseau d'entreprise

```js
app.commandLine.appendSwitch("auth-server-allowlist", "*");
app.commandLine.appendSwitch("auth-negotiate-delegate-allowlist", "*");
```

Ces deux options autorisent Chromium à répondre automatiquement aux
authentifications intégrées (Kerberos / NTLM) exigées par les proxys
d'entreprise. Sans elles, le téléchargement des modèles et la vérification des
mises à jour échouent derrière un proxy authentifié, sans message exploitable.

Le caractère générique `*` accorde cette délégation à **tous** les hôtes. C'est
le réglage permissif ; une liste explicite serait plus restrictive.

---

## 10. Limites connues

### 10.1 Trois sondages simultanés sur le même backend

| Origine | Cible | Fréquence |
|---|---|---|
| processus principal — état de la barre des tâches | `/api/record/status` | 4 s |
| processus principal — notification « CR prêt » | **`/api/jobs`** | 5 s |
| renderer — liste des réunions | **`/api/jobs`** | 2,5 s |

`/api/jobs` renvoie le markdown et le transcript intégraux de **tout**
l'historique (brique 4 §12.2). Il est donc récupéré en entier **deux fois par
tranche de 5 secondes**, par deux processus différents, alors que le processus
principal n'a besoin que des champs `id` et `status`.

C'est le même défaut que celui signalé côté backend, mais amplifié : l'alléger
profiterait aux deux.

### 10.2 Le délai de 90 secondes ne distingue pas lent de cassé

Voir §3. Un démarrage à froid particulièrement long produit le même message
qu'un backend qui ne démarre pas du tout.

### 10.3 L'état des mises à jour est invisible

Voir §8. Ni version affichée, ni date de dernière vérification, ni signalement
d'échec.

### 10.4 La délégation d'authentification est ouverte à tous les hôtes

Voir §9.

### 10.5 Une application qui ne se ferme pas vraiment

Le mode barre des tâches est en retrait volontaire, et `window-all-closed` ne
quitte pas. C'est le comportement recherché, mais il surprend : la découverte se
fait par la popup affichée à la première fermeture. Si l'utilisateur la ferme
sans lire, il n'a plus d'indication que l'application tourne, hors l'icône.

### 10.6 Aucun test automatisé

Comme les briques précédentes. `electron/test_downloader.js` existe mais ne
couvre que le téléchargement (brique 7).

---

## 11. Vérifier

```powershell
# terminal 1 — frontend en rechargement à chaud
cd webapp ; npm run dev

# terminal 2 — Electron + backend depuis les sources
& ".\meeting_assistant\Scripts\Activate.ps1"
cd electron ; npm run dev:hot
```

Voir [WORKFLOW.md](../../WORKFLOW.md) pour le détail des deux modes de
développement et de la publication.

**Traces à suivre au démarrage :**

| Trace | Signification |
|---|---|
| `[electron] spawn backend: …` | commande réellement lancée — vérifie le mode dev/prod |
| `[backend] …` | sortie du processus Python, relayée |
| `[electron] backend exited (code=…)` | arrêt du backend ; un code non nul en cours de session est anormal |
| `[updater] …` | seule trace des mises à jour (§8) |

**Points de contrôle :**

- Fermer la fenêtre doit **cacher** l'application, pas la quitter. Vérifier que
  l'icône reste dans la barre des tâches et que le processus `backend.exe` vit
  toujours.
- Pendant un enregistrement, l'icône doit porter la pastille rouge et le menu
  afficher la durée écoulée.
- Après une mise à jour acceptée, aucun `backend.exe` ni `llama-server.exe` ne
  doit subsister dans le gestionnaire de tâches — sinon l'installeur restera
  bloqué (§3).

---

## 12. Résumé pour une reprise

1. Electron est le **superviseur de processus** : il démarre le backend, lui
   transmet les chemins des modèles par variables d'environnement, attend
   `/api/health`, et le tue par **arbre de processus** (uvicorn et llama-server
   engendrent des fils).
2. La séquence de démarrage est ordonnée et bloquante : modèles → splash →
   backend → attente → fenêtre. Toute erreur ferme proprement.
3. Le frontend parle au backend **en HTTP direct**. Le préchargement n'expose
   qu'une URL et des canaux d'événements — isolation du contexte, pas
   d'intégration Node, bac à sable actif.
4. L'application **vit en arrière-plan par défaut** : fermer la fenêtre la
   cache. Elle ne quitte que par le menu de la barre des tâches ou le réglage
   `quitOnClose`.
5. `stopBackendAndWait()` avant `quitAndInstall()` n'est pas une précaution
   théorique : sans elle, l'installeur NSIS se bloque sur des fichiers
   verrouillés.
6. Trois mécanismes de notification indépendants, tous par sondage du backend
   depuis le processus principal.

**Premier chantier si l'on doit optimiser :** les trois sondages simultanés
(§10.1), dont deux récupèrent l'intégralité de l'historique toutes les
5 secondes.
