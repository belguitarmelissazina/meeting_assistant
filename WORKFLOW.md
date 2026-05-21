# Workflow — Meeting Assistant

Aide-mémoire des gestes qui se répètent : tester en dev, puis publier une nouvelle version sur GitHub (qui déclenche l'auto-update chez les utilisateurs).

---

## 1. Tester pendant le développement (2 terminaux, hot reload)

> Pas besoin de builder. Tu modifies → tu vois.

### Terminal 1 — serveur webapp (Next.js, hot reload)
```powershell
cd "c:\Users\MelissaBELGUITAR\OneDrive - YELE CONSULTING\Bureau\diarisation-final\webapp"
npm run dev
```
Laisse tourner. Toute modif `webapp/**/*.tsx` est rechargée instantanément.

### Terminal 2 — Electron + backend Python (depuis les sources)
```powershell
& "c:\Users\MelissaBELGUITAR\OneDrive - YELE CONSULTING\Bureau\diarisation-final\meeting_assistant\Scripts\Activate.ps1"
cd "c:\Users\MelissaBELGUITAR\OneDrive - YELE CONSULTING\Bureau\diarisation-final\electron"
npm run dev:hot
```
(`dev:hot` pointe Electron sur `http://localhost:3000`. Le backend Python est lancé depuis les sources, aucune compilation.)

### À chaque modif
| Modifié | À faire |
|---|---|
| `webapp/**` (React, CSS…) | **rien**, hot reload auto (sauve le fichier) |
| `backend/**` (Python) | ferme + relance le **Terminal 2** |
| `electron/main.js` / `preload.js` / `build-app.js` | ferme + relance le **Terminal 2** |

---

## 2. Publier une nouvelle version (auto-update GitHub)

> À faire dès que tu veux que les postes installés reçoivent tes modifs.

### Pré-vol (5 secondes)
1. Vérifie `electron/.env` (contient `GH_TOKEN` write + `GH_READ_TOKEN` read).
2. **Bumpe la version** dans `electron/package.json` → `"version": "X.Y.Z"` → `"X.Y.(Z+1)"` (ex. `0.2.0` → `0.3.0`). **Obligatoire**, sinon les postes ne verront pas qu'il y a du nouveau.
3. **OneDrive en pause** (icône tray → Suspendre la synchro 2 h). Sinon erreurs *read-only* au build.
4. **Supprime à la main** dans `…\diarisation-final\` :
   - `dist\`
   - `build\backend\` (le dossier, **garde** `build\backend.spec`)
   - `release\`

### Build + publication
```powershell
& "c:\Users\MelissaBELGUITAR\OneDrive - YELE CONSULTING\Bureau\diarisation-final\meeting_assistant\Scripts\Activate.ps1"
cd "c:\Users\MelissaBELGUITAR\OneDrive - YELE CONSULTING\Bureau\diarisation-final\electron"
npm run publish
```
Durée : ~5-15 min (PyInstaller). Résultat :
- L'installeur local : `release\MeetingAssistant-Setup-X.Y.Z.exe`
- La release **vX.Y.Z** publiée sur GitHub : `meeting-assistant-releases` avec `MeetingAssistant-Setup-X.Y.Z.exe` + `.blockmap` + `latest.yml`.

### Vérifier
- Sur GitHub : repo `meeting-assistant-releases` → onglet **Releases** → la version doit apparaître avec les 3 assets ci-dessus.
- Sur ton poste : **relance l'app déjà installée** depuis le menu Démarrer (pas l'installeur). Quelques secondes plus tard → boîte « Mise à jour prête » → Redémarrer → app à jour ✅.

---

## 3. Pièges OneDrive (ils peuvent revenir à chaque build)

- **Build webapp plante** sur `.next` (`EINVAL readlink`) → supprime `webapp\.next` à la main, relance.
- **PyInstaller plante** sur `dist\backend\_internal\...` (« Accès refusé ») → vérifie que `dist\` et `build\backend\` ont bien été supprimés ; tue tout process **backend.exe** / **llama-server.exe** restant dans le Gestionnaire des tâches ; relance.
- **electron-builder plante** sur `release\` (idem) → supprime `release\` à la main, relance.
- **Mise à jour figée sur le poste de test** (assistant d'install bloqué) → ouvre le **Gestionnaire des tâches** → termine **Meeting Assistant**, **backend.exe**, **llama-server.exe** → l'installeur reprend ou tu cliques Annuler + relances l'installeur à la main une fois.

---

## 4. Numéros de version (rappel)

- `0.X.Y` → bump `Y` pour un correctif, `X` pour des fonctionnalités, garde `0.` tant que c'est interne.
- La version dans `electron/package.json` est **la seule** à modifier (elle pilote l'auto-update).
- L'auto-update se déclenche **uniquement si** la version publiée est **strictement supérieure** à la version installée.

---

## 5. Secrets / sécurité (rappel)

- `electron/.env` est **gitignoré** : il n'est ni committé ni embarqué dans l'app distribuée.
- Le **jeton READ** est embarqué dans l'app (lecture seule, scopé au seul repo `meeting-assistant-releases`) → c'est lui qui permet à l'app de télécharger les MAJ depuis le repo privé.
- Le **jeton WRITE** reste **uniquement sur ta machine de build**, jamais distribué.
- Aucun jeton Microsoft / aucune donnée utilisateur n'est embarqué dans l'app.
