# Webapp — Diarisation & Compte rendu

Interface Next.js 15 / React 19 / TypeScript / Tailwind branchee sur le pipeline
Python (`diar_pipeline` + `meeting_minutes_pipeline.py` + `audio_capture`).

## Palette

| Token              | Couleur   | Usage                              |
| ------------------ | --------- | ---------------------------------- |
| `brand`            | `#ab3723` | Boutons primaires, titres `h1`     |
| `brand-dark`       | `#8a2d1a` | Hover, bouton danger, titres `h2`  |
| `accent-blue`      | `#2f728c` | Liens, focus, infos, icones upload |
| `accent-green`     | `#699747` | Succes, etape transcription        |
| `accent-yellow`    | `#d8a925` | Fonds / accents uniquement (jamais texte ni icone) |

## Demarrage

```bash
cd webapp
npm install
npm run dev      # http://localhost:3000
```

Le pipeline Python doit etre fonctionnel a la racine du projet (`python -m diar_pipeline.run` et `python meeting_minutes_pipeline.py` doivent passer).

## Architecture

```
webapp/
  app/
    page.tsx                       UI principale (record / upload / job)
    api/record/start|stop          Demarre/arrete AudioRecorder via record_bridge.py
    api/process/upload             Upload fichier + lance pipeline
    api/jobs/[id]                  Statut + log d'un job
    api/jobs/[id]/download         Telecharge MD ou transcript
  components/
    Recorder.tsx                   Boutons start/stop + minuterie
    Uploader.tsx                   Drag & drop fichier audio
    JobPanel.tsx                   Progression + tabs (CR / transcript / log)
  lib/jobs.ts                      Job store (in-memory) + spawn Python
  scripts/record_bridge.py         Pont AudioRecorder ↔ API (file flag)
```

## Notes prod

- Le job store est **en memoire** : redemarre = jobs perdus. Pour la prod, le brancher sur SQLite/Postgres.
- Le `record_bridge.py` utilise un fichier `stop.flag` (pas de signal POSIX) pour fonctionner sur Windows.
- L'enregistrement WASAPI loopback ne fonctionne **que sur la machine** qui execute Next.js (ce n'est pas une capture cote navigateur).
