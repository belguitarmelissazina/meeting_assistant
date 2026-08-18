# Brique 6 — Frontend (Next.js)

**Dossier :** [webapp/](../../webapp/) — 18 composants, 5 modules `lib/`,
2 pages, 1 feuille de style
**Rôle :** l'interface de l'application, servie en statique et chargée par
Electron.

> **Périmètre.** Ce document décrit la version **livrée**. La fenêtre flottante
> de l'assistant Mistral (`app/live-advisor/`) et les modifications
> correspondantes de `Recorder.tsx` et `tray-popup/page.tsx` ne sont pas
> suivies par git : elles ne sont pas documentées.

---

## 1. Une application à état, pas un site à routes

Next.js est utilisé en **export statique**. Il n'y a que deux pages :

| Route | Chargée par | Rôle |
|---|---|---|
| `/` | fenêtre principale d'Electron | toute l'application |
| `/tray-popup` | popup de la barre des tâches | interface réduite |

La page `/` n'utilise **aucun routage**. [app/page.tsx](../../webapp/app/page.tsx)
détient trois états qui déterminent à eux seuls ce qui s'affiche :

```
nav          : "agenda" | "reports" | "folders" | "capture"
selected     : TimelineItem | null      ← une réunion ouverte par-dessus
folderFilter : string | null | undefined ← undefined = tous, null = sans dossier
```

```
selected ?          → MeetingDetail        (une réunion : compte rendu + transcript)
nav = "capture"     → OnboardingView       (enregistrer / importer)
nav = "reports"     → ReportsPage
nav = "folders"     → folderFilter défini ? ReportsPage(filtré) : FoldersPage
sinon               → MeetingsHome         (agenda + timeline)  ← vue par défaut
```

C'est cohérent avec la cible : dans une fenêtre Electron chargée depuis
`file://`, une URL ne se partage pas et le bouton « précédent » n'existe pas.
Le prix à payer est que **la navigation n'est pas adressable** — rien ne
permet de rouvrir directement une réunion par un lien.

### Le raccord avec Electron

[lib/api.ts](../../webapp/lib/api.ts) résout l'adresse du backend en trois
temps :

```ts
window.electronAPI?.backendUrl      // dans Electron
?? process.env.NEXT_PUBLIC_BACKEND_URL   // développement navigateur
?? "http://127.0.0.1:8000"               // repli
```

C'est ce qui permet d'ouvrir l'interface dans un simple navigateur, sans
Electron, pendant le développement.

Le pont de préchargement (brique 5 §5) sert uniquement aux **événements** :
`page.tsx` s'abonne à trois canaux au montage.

| Canal | Effet |
|---|---|
| `notifications.onOpenMeeting` | bascule sur l'agenda et mémorise la réunion à ouvrir |
| `tray.onOpenJob` | ouvre directement la réunion (clic sur « Compte rendu prêt ») |
| `tray.onFirstHideHint` | affiche une notification web expliquant que l'app tourne encore |

Le troisième mérite un détour : la fenêtre venant d'être cachée, **une popup
dans l'interface serait invisible**. Le renderer déclenche donc une
`Notification` web, et pose un drapeau dans `localStorage` pour ne le faire
qu'une fois.

---

## 2. La synchronisation d'état : du sondage, partout

Il n'y a ni WebSocket, ni `EventSource`, ni gestionnaire d'état global. Chaque
composant qui a besoin d'une donnée fraîche la redemande à intervalle fixe.

La justification est écrite dans
[useRecordingStatus.ts](../../webapp/lib/useRecordingStatus.ts#L23) :

> *Pourquoi un poll au lieu d'un EventSource/WS : un seul enregistrement actif à
> la fois, 2 s de latence est largement acceptable, et ça reste robuste si le
> backend reboot pendant que l'app tourne (le hook re-converge tout seul).*

L'argument de robustesse est réel : un backend redémarré ne casse rien, le tick
suivant reconverge.

### Le tableau complet

| Origine | Cible | Intervalle |
|---|---|---|
| `useJobs` — **Sidebar** | `/api/jobs` + `/api/folders` | 2,5 s |
| `useJobs` — **SearchOverlay** | idem | 2,5 s |
| `useJobs` — ReportsPage *(si affichée)* | idem | 2,5 s |
| `useJobs` — FoldersPage *(si affichée)* | idem | 2,5 s |
| `useRecordingStatus` — Sidebar | `/api/record/status` | 2 s |
| `useRecordingStatus` — MeetingsHome | idem | 2 s |
| JobPanel *(réunion ouverte)* | `/api/jobs/{id}` | 1,5 s |
| MeetingsHome *(connecté à l'agenda)* | `/api/jobs` | 4 s |
| MeetingsHome *(connexion en cours)* | `/api/calendar/status` | 3 s |
| Sidebar | `/api/calendar/status` | 10 s |
| tray-popup *(si ouverte)* | `/api/calendar/upcoming` + `/api/jobs` | 4 s |

> ⚠ **`useJobs` n'est pas mutualisé.** Sa documentation le dit :
> *« Chaque consommateur a son propre intervalle. »* Le code de récupération
> n'est plus dupliqué, mais les requêtes le sont.
>
> Et **`SearchOverlay` appelle `useJobs()` même fermé** — il est rendu en
> permanence par `page.tsx` avec une simple propriété `open`, et un hook ne peut
> pas être conditionnel. Il sonde donc en continu une liste qu'il n'affiche pas.

**Au repos sur la page d'accueil**, `/api/jobs` est donc récupéré par la barre
latérale, la recherche, la vue d'accueil, plus le processus principal d'Electron
(brique 5 §10.1) — soit **environ deux fois par seconde**, chaque réponse
contenant l'intégralité des comptes rendus et transcripts de tout l'historique
(brique 4 §12.2).

Les trois briques signalent le même défaut ; c'est ici qu'on en voit
l'accumulation.

---

## 3. La timeline unifiée

[lib/meetings.ts](../../webapp/lib/meetings.ts) fusionne deux sources qui ne se
connaissent pas :

```
/api/calendar/upcoming   →  réunions à venir (Microsoft Graph)
/api/jobs                →  réunions enregistrées

clé de liaison : job.calendar.eventId === event.id
```

`buildTimeline()` produit deux listes : les **à venir** (événements d'agenda
sans job associé, triés par heure croissante) et les **enregistrées** (tous les
jobs, plus récents d'abord).

Un événement d'agenda **disparaît des « à venir » dès qu'il a été enregistré** —
c'est le job qui le représente désormais.

### Trois règles métier qui vivent ici

**Le nom affiché.** `meetingDisplayName()` : si le libellé ressemble à un
dossier auto-daté (`2026-05-19_14h00m00s…`) et qu'un sujet d'agenda existe, on
affiche le sujet. Un renommage manuel gagne toujours.

**Les entreprises devinées.** `guessCompanies()` extrait le domaine de chaque
adresse mail, écarte une liste de fournisseurs grand public (gmail, orange,
free, proton…), et capitalise ce qui reste. Ce sont les valeurs pré-remplies
dans le champ « entreprises » qui alimentera les *entités figées* du prompt
(brique 3 §3.4).

**Les dates de Graph.** `parseGraphDate()` retire les fractions de seconde
avant l'analyse. Le commentaire assume l'hypothèse : *« l'utilisateur est sur un
PC à l'heure de Paris donc l'affichage local est correct »* — Graph renvoie
l'heure locale sans décalage horaire.

---

## 4. Le pré-remplissage depuis l'agenda

[lib/calendarPrefill.ts](../../webapp/lib/calendarPrefill.ts) est un **module
singleton** de trois fonctions autour d'une variable.

```ts
setCalendarPrefill(p)      // depuis la fiche réunion
consumeCalendarPrefill()   // lit ET vide — sémantique « une seule fois »
peekCalendarPrefill()      // lit sans vider
clearCalendarPrefill()
```

Le choix est justifié dans le fichier : le trajet de la donnée est
`CalendarPanel → changement d'onglet → Recorder → enregistrement →
onJobCreated → JobPanel → DraftForm`. La faire descendre en propriétés
alourdirait cinq composants pour une donnée consommée une fois. Comme
l'application est une page unique sans rechargement, un module suffit.

Ce que ça transporte : participants, entreprises devinées, et un contexte
composé (sujet, organisateur, lieu, réunion en ligne, puis **la description
complète** de l'invitation). Le commentaire précise que la description n'est
pas tronquée volontairement — elle part telle quelle dans le *system prompt* du
backend, et couper masquerait des sigles ou instructions utiles.

---

## 5. La vue réunion

[MeetingDetail.tsx](../../webapp/components/MeetingDetail.tsx) est le cœur de
l'interface.

### Des onglets, dont un optionnel

- **Compte rendu** — toujours présent, non fermable.
- **Transcript** — ouvert par un bouton, fermable par une croix. Son état est
  persisté en `localStorage`, pour que la disposition suive l'utilisateur d'une
  réunion à l'autre.

### Un seul élément audio, monté haut

```
MeetingDetail
   ├─ <audio ref={audioRef}>        ← monté une seule fois, dès qu'un audio existe
   ├─ JobPanel        (lecteur visible, contrôles)
   └─ TranscriptView  (reçoit audioRef : seek + surlignage)
```

L'élément est monté au niveau de `MeetingDetail` **même quand le lecteur n'est
pas visible**. Sans cela, la vue transcript ne pourrait pas se synchroniser
avant que l'utilisateur ait ouvert le lecteur.

Corollaire soigné : cliquer sur une ligne du transcript déclenche le `seek`
**et** demande au parent d'afficher le lecteur — sinon l'audio se lancerait sans
aucun contrôle visible, ni pause ni curseur.

---

## 6. La vue transcript

[TranscriptView.tsx](../../webapp/components/TranscriptView.tsx) consomme
`GET /api/jobs/{id}/turns`, c'est-à-dire `turns.json` et `speakers.json` — les
deux fichiers dont les briques 1, 2 et 4 décrivent la production.

### Synchronisation avec l'audio

Un écouteur `timeupdate` cherche le tour de parole contenant l'instant courant.
La recherche est **linéaire**, et le commentaire l'assume : quelques centaines
de tours pour une réunion d'une heure, une recherche dichotomique n'apporterait
rien.

Le défilement automatique n'a lieu que si **l'index change et que l'élément est
hors du cadre visible** — sinon la liste vibrerait à chaque impulsion de
l'audio.

### Renommage des locuteurs

L'interface propose les participants issus de l'agenda pour remplacer
`SPEAKER_00`. La mise à jour est **optimiste** : l'état local change
immédiatement, la requête `PATCH` part ensuite, et en cas d'échec on recharge
depuis le backend pour resynchroniser.

Le mapping est stocké séparément côté backend ; `turns.json` conserve les
étiquettes brutes (brique 4 §6). Un renommage reste donc toujours réversible.

---

## 7. L'éditeur de compte rendu

[ReportEditor.tsx](../../webapp/components/ReportEditor.tsx) est la partie la
plus délicate du frontend.

```
compte_rendu.md
   └─ marked      → HTML  → tiptap (édition WYSIWYG)
                                │  (frappe)
                                ▼
                            debounce 1 s
                                │
      markdown ← turndown ← HTML de l'éditeur
                                │
                    PATCH /api/jobs/{id}/report
                                │
                    le backend réécrit le .md ET régénère le .docx
```

Chaque sauvegarde traverse donc **markdown → HTML → markdown**.

### Trois règles maison pour les tableaux

Le convertisseur standard ne suffisait pas, et le fichier explique pourquoi :

> *La règle table de `turndown-plugin-gfm` laisse le tableau en HTML brut dès
> que la 1ʳᵉ ligne ne passe pas son `isHeadingRow` strict (tiptap émet
> `<table class="md-table"><tbody><tr><th><p>…` avec des `<p>`/blancs). Le
> backend (`_md_to_docx`) ne lit QUE le GFM `| … |` → docx cassé.*

D'où trois ajouts :

| Règle | Rôle |
|---|---|
| `cellParagraphUnwrap` | retire les `<p>` que tiptap place dans les cellules |
| `gfmTable` | **reconstruit** tout `<table>` en GFM déterministe, en normalisant le nombre de colonnes et en échappant les barres verticales |
| `tableTagsPassthrough` | filet de sécurité : aucune balise de tableau ne doit survivre en HTML |

`turndown.escape` est par ailleurs neutralisé : l'éditeur garantissant la
structure, l'échappement ne ferait que polluer la sortie de `1\.` et `\*`.

C'est un exemple net de couplage entre briques : le format produit ici doit
correspondre exactement à ce que le convertisseur DOCX du backend sait lire
(brique 4 §8).

> ⚠ **L'aller-retour n'est pas neutre.** Ouvrir un compte rendu et taper un seul
> caractère réécrit **tout** le fichier tel que `turndown` le re-sérialise —
> espacements, style des titres, marqueurs de liste. Le résultat reste du
> markdown valide et lisible par le backend, mais ce n'est pas nécessairement
> l'octet à octet de ce que le LLM avait produit.

---

## 8. Les autres composants

| Composant | Rôle |
|---|---|
| `Sidebar` | navigation, réunions récentes, pastille « enregistrement en cours » cliquable, accès aux paramètres |
| `MeetingsHome` | vue d'accueil : agenda + timeline fusionnée, connexion Microsoft |
| `OnboardingView` | page capture : enregistrer, importer un audio, importer un transcript |
| `Recorder` | bouton d'enregistrement, minuteur, reprise d'un enregistrement déjà en cours au montage |
| `JobPanel` | état du traitement, sélecteur **local / Mistral**, lecteur audio, actions |
| `ReportsPage` / `FoldersPage` | listes, filtrage par dossier |
| `JobHistory` | liste groupée par jour |
| `SearchOverlay` | recherche globale (`Ctrl+F` hors réunion) |
| `ReportFindBar` | recherche **dans** le compte rendu — délègue à `findInPage` d'Electron (brique 5 §4) |
| `SettingsDialog` | clé Mistral, compte Microsoft, préférences de fenêtre |
| `TranscriptUploader` / `Uploader` | envoi de fichiers |
| `MiniCalendar`, `ThemeToggle` | utilitaires d'affichage |

Deux comportements notables :

- **`Recorder` reprend un enregistrement en cours.** Au montage, il interroge
  `/api/record/status` : si le backend enregistre déjà, il restitue le minuteur
  et le bouton « Arrêter ». C'est ce qui rend la pastille de la barre latérale
  fonctionnelle après une navigation.
- **`Ctrl+F` a deux comportements.** Sans réunion ouverte, il ouvre la recherche
  globale ; avec une réunion ouverte, `ReportFindBar` le capte et lance la
  recherche native d'Electron.

---

## 9. Limites connues

### 9.1 Le sondage se multiplie par le nombre de composants montés

Voir §2. `useJobs` n'est pas mutualisé, et `SearchOverlay` sonde même fermé.
Mutualiser ce hook — un unique intervalle, un contexte React partagé — diviserait
le trafic par deux ou trois sans toucher au backend.

### 9.2 L'aller-retour de l'éditeur réécrit tout le fichier

Voir §7.

### 9.3 La navigation n'est pas adressable

Voir §1. Ni lien profond, ni historique de navigation. Acceptable dans une
fenêtre Electron, bloquant si l'interface devait un jour être servie sur le web.

### 9.4 Le fuseau horaire est supposé

`parseGraphDate` (§3) part du principe que le poste est à l'heure de Paris. Un
utilisateur en déplacement verrait des heures décalées.

### 9.5 Aucun test automatisé

Comme les briques précédentes. Ni test unitaire, ni test de rendu.

---

## 10. Vérifier

```powershell
cd webapp
npm run dev        # http://localhost:3000
```

L'interface fonctionne dans un navigateur ordinaire, sans Electron : `lib/api.ts`
retombe sur `http://127.0.0.1:8000` (§1). Il suffit que le backend tourne.

Ce qui **ne fonctionne pas** hors Electron : la recherche dans le compte rendu
(`findInPage`), les notifications natives, la reprise depuis la barre des tâches
— tout ce qui passe par `window.electronAPI`. Le code utilise systématiquement
l'appel optionnel `?.` pour que l'absence du pont ne casse rien.

Pour le mode complet, voir [WORKFLOW.md](../../WORKFLOW.md) : `npm run dev:hot`
côté Electron pointe la fenêtre sur le serveur de développement.

**Points de contrôle :**

- L'onglet réseau des outils de développement montre le rythme réel des
  sondages (§2) — c'est le moyen le plus direct de constater le problème.
- Après édition d'un compte rendu, vérifier que `compte_rendu.docx` a bien été
  régénéré et que les **tableaux** y sont des tableaux Word, pas du texte brut :
  c'est ce que valident les trois règles de conversion (§7).
- Un renommage de locuteur doit survivre à un rechargement de la fenêtre : il
  est persisté dans `speakers.json`, pas seulement en mémoire.

---

## 11. Résumé pour une reprise

1. **Pas de routage** : une seule page, trois variables d'état commutent entre
   cinq vues. Second point d'entrée `/tray-popup` pour la barre des tâches.
2. **Pas de gestionnaire d'état, pas de WebSocket** : tout est du sondage HTTP
   direct vers le backend. Le raccord Electron ne sert qu'aux événements.
3. Le sondage **se multiplie par le nombre de composants montés** — c'est le
   principal levier d'optimisation du frontend (§9.1).
4. La **timeline** fusionne agenda et réunions enregistrées par
   `job.calendar.eventId`. Les règles de nommage, de devinette d'entreprises et
   de composition du contexte vivent dans `lib/meetings.ts`.
5. L'**éditeur** fait un aller-retour markdown → HTML → markdown à chaque
   sauvegarde, avec trois règles de conversion maison pour que les tableaux
   restent lisibles par le convertisseur DOCX du backend.
6. La **vue transcript** est le point de convergence des briques 1, 2 et 4 :
   elle consomme `turns.json` et `speakers.json`, et se synchronise à l'audio
   par un élément monté au niveau de `MeetingDetail`.

**Premier chantier si l'on doit optimiser :** mutualiser `useJobs` en un
intervalle unique partagé (§9.1). C'est du code frontend seul, sans impact sur
le backend, et cela réduit immédiatement le trafic le plus lourd de
l'application.
